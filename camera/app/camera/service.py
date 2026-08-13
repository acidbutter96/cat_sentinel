"""RTSPCamera: a background thread that connects to the Tapo C200's
RTSP/H.264 stream (`/stream1` HD or `/stream2` SD -- see settings.camera_rtsp_path),
continuously decodes it, and keeps a single shared "latest frame" JPEG
buffer that every consumer (live view, snapshot, recording) reads from.

IP camera firmware in general tends to choke on too many simultaneous RTSP
connections, so this process opens exactly ONE RTSP connection, ever, and
every domain that needs frames reads the shared buffer instead of
connecting again -- see app.core.dependencies.get_camera and
app.recordings for how recording reuses this same decode loop rather than
opening a second stream.
"""

from __future__ import annotations

import contextlib
import io
import logging
import threading
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import av

from app.settings.config import settings

logger = logging.getLogger(__name__)

RECONNECT_DELAY_SECONDS = 5.0
CONNECT_TIMEOUT_SECONDS = 10.0


@dataclass
class CameraStatusSnapshot:
    connected: bool
    transport: str
    last_error: str | None
    frame_age_seconds: float | None


@dataclass
class RecordingStatusSnapshot:
    is_recording: bool
    filename: str | None
    started_at: float | None
    elapsed_seconds: float | None


class RTSPCamera:
    """Owns the single RTSP connection to the camera. Call start() once at
    app startup and stop() once at shutdown; reset() tears down and
    reconnects on demand (POST /camera/reset).
    """

    def __init__(self, rtsp_url: str, transport: str = "tcp") -> None:
        self.rtsp_url = rtsp_url
        self.transport = transport

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._latest_jpeg: bytes | None = None
        self._last_frame_monotonic: float | None = None
        self._last_frame_size: tuple[int, int] | None = None
        self._connected = False
        self._last_error: str | None = None

        # Recording state -- writes reuse frames from the same decode loop.
        self._recording = False
        self._record_filename: str | None = None
        self._record_started_monotonic: float | None = None
        self._out_container: av.container.OutputContainer | None = None
        self._out_stream = None
        self._record_frame_index = 0

    # --- lifecycle -----------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="rtsp-camera", daemon=True)
        self._thread.start()
        logger.info("RTSPCamera thread started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=CONNECT_TIMEOUT_SECONDS)
        self._thread = None
        self._close_recording_locked_safe()
        logger.info("RTSPCamera thread stopped")

    def reset(self) -> None:
        """Forces a full teardown and reconnect."""
        logger.info("RTSPCamera reset requested")
        self.stop()
        self.start()

    def is_running(self) -> bool:
        """True while the background decode thread is alive and hasn't been
        intentionally stopped. NOT the same as "connected" -- the thread
        stays alive and keeps retrying across transient disconnects; callers
        that only care about live frames should check get_status().connected
        or whether get_frame() returns data.
        """
        return (
            self._thread is not None
            and self._thread.is_alive()
            and not self._stop_event.is_set()
        )

    # --- hot path: called dozens of times/sec by streaming consumers ---
    # Deliberately NOT decorated with @log_call/@log_errors -- see the
    # module docstring in app/core/decorators.py. Entry-logging every frame
    # read would flood the logs and add real overhead to the MJPEG stream.

    def get_frame(self) -> bytes | None:
        with self._lock:
            return self._latest_jpeg

    def get_status(self) -> CameraStatusSnapshot:
        with self._lock:
            frame_age = (
                time.monotonic() - self._last_frame_monotonic
                if self._last_frame_monotonic is not None
                else None
            )
            return CameraStatusSnapshot(
                connected=self._connected,
                transport=self.transport,
                last_error=self._last_error,
                frame_age_seconds=frame_age,
            )

    # --- recording (reuses this same decode loop's frames) -------------

    def start_recording(self, filename: str, output_dir: Path) -> None:
        with self._lock:
            if self._recording:
                raise RuntimeError("A recording is already in progress")
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / filename
            width, height = self._last_frame_size or (1280, 720)
            out_container = av.open(str(path), mode="w")
            out_stream = out_container.add_stream("mpeg4", rate=15)
            out_stream.width = width
            out_stream.height = height
            out_stream.pix_fmt = "yuv420p"
            self._out_container = out_container
            self._out_stream = out_stream
            self._record_filename = filename
            self._record_started_monotonic = time.monotonic()
            self._record_frame_index = 0
            self._recording = True
        logger.info("recording started: %s", filename)

    def stop_recording(self) -> RecordingStatusSnapshot:
        with self._lock:
            if not self._recording:
                raise RuntimeError("No recording is currently in progress")
            filename = self._record_filename
            started_at = self._record_started_monotonic
            elapsed = time.monotonic() - (started_at or time.monotonic())
            self._finalize_recording_locked_safely()
            snapshot = RecordingStatusSnapshot(
                is_recording=False,
                filename=filename,
                started_at=started_at,
                elapsed_seconds=elapsed,
            )
        logger.info("recording stopped: %s", filename)
        return snapshot

    def get_recording_status(self) -> RecordingStatusSnapshot:
        with self._lock:
            elapsed = (
                time.monotonic() - self._record_started_monotonic
                if self._record_started_monotonic is not None
                else None
            )
            return RecordingStatusSnapshot(
                is_recording=self._recording,
                filename=self._record_filename,
                started_at=self._record_started_monotonic,
                elapsed_seconds=elapsed,
            )

    def _flush_and_close_output_locked(self) -> None:
        """Caller must hold self._lock."""
        if self._out_container is None:
            return
        try:
            if self._out_stream is not None:
                for packet in self._out_stream.encode():
                    self._out_container.mux(packet)
        finally:
            self._out_container.close()
            self._out_container = None
            self._out_stream = None

    def _finalize_recording_locked_safely(self) -> None:
        """Flush and close the output; caller must hold self._lock."""
        if self._out_container is not None:
            try:
                self._flush_and_close_output_locked()
            except Exception:  # noqa: BLE001 -- close must still reset state
                logger.exception("failed to finalize recording %s", self._record_filename)
        self._recording = False
        self._record_filename = None
        self._record_started_monotonic = None
        self._record_frame_index = 0

    def _close_recording_locked_safe(self) -> None:
        with self._lock:
            self._finalize_recording_locked_safely()

    # --- background decode loop -----------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            container = None
            try:
                options = {"rtsp_transport": self.transport, "stimeout": "10000000"}
                container = av.open(self.rtsp_url, options=options, timeout=CONNECT_TIMEOUT_SECONDS)
                with self._lock:
                    self._connected = True
                    self._last_error = None
                logger.info("connected to camera RTSP stream (%s)", self.transport)

                for frame in container.decode(video=0):
                    if self._stop_event.is_set():
                        break
                    self._process_frame(frame)

            except Exception as exc:  # noqa: BLE001 -- reconnect loop must survive any decode/connect failure
                with self._lock:
                    self._connected = False
                    self._last_error = str(exc)
                logger.error("RTSP connection error: %s", exc)
            finally:
                if container is not None:
                    with contextlib.suppress(Exception):
                        container.close()
                with self._lock:
                    self._connected = False

            if not self._stop_event.is_set():
                time.sleep(RECONNECT_DELAY_SECONDS)

    def _process_frame(self, frame: av.VideoFrame) -> None:
        # JPEG-encode the decoded frame for the live-view / snapshot buffer.
        image = frame.to_image()  # PIL.Image, RGB
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=settings.live_jpeg_quality)
        jpeg_bytes = buf.getvalue()

        with self._lock:
            self._latest_jpeg = jpeg_bytes
            self._last_frame_monotonic = time.monotonic()
            self._last_frame_size = (frame.width, frame.height)

            if self._recording and self._out_container is not None and self._out_stream is not None:
                try:
                    out_frame = frame.reformat(
                        width=self._out_stream.width,
                        height=self._out_stream.height,
                        format="yuv420p",
                    )
                    out_frame.pts = self._record_frame_index
                    out_frame.time_base = Fraction(1, 15)
                    self._record_frame_index += 1
                    for packet in self._out_stream.encode(out_frame):
                        self._out_container.mux(packet)
                except Exception:  # noqa: BLE001 -- a single bad frame must not kill the decode loop
                    logger.exception("failed to write frame to recording %s", self._record_filename)
                    self._finalize_recording_locked_safely()
