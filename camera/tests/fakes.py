"""Test doubles -- kept out of the app package since they're fixtures, not
part of the application.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.camera.service import CameraStatusSnapshot, RecordingStatusSnapshot
from app.ptz.service import PTZStatus


class FakeCamera:
    """Stands in for RTSPCamera in tests: no real thread, no real RTSP
    connection, just enough state to exercise the camera router.
    """

    def __init__(self, connected: bool = True, frame: bytes | None = b"\xff\xd8fakejpeg\xff\xd9"):
        self._connected = connected
        self._frame = frame
        self._running = True
        self._reset_called = 0
        self._recording = False
        self._record_filename: str | None = None
        self._record_started: float | None = None

    def is_running(self) -> bool:
        return self._running

    def get_frame(self) -> bytes | None:
        return self._frame

    def get_status(self) -> CameraStatusSnapshot:
        return CameraStatusSnapshot(
            connected=self._connected,
            transport="tcp",
            last_error=None,
            frame_age_seconds=0.1 if self._frame else None,
        )

    def reset(self) -> None:
        self._reset_called += 1
        self._connected = True

    def start_recording(self, filename: str, output_dir: Path) -> None:
        if self._recording:
            raise RuntimeError("A recording is already in progress")
        self._recording = True
        self._record_filename = filename
        self._record_started = time.monotonic()

    def stop_recording(self) -> RecordingStatusSnapshot:
        if not self._recording:
            raise RuntimeError("No recording is currently in progress")
        filename = self._record_filename
        elapsed = time.monotonic() - (self._record_started or time.monotonic())
        self._recording = False
        self._record_filename = None
        self._record_started = None
        return RecordingStatusSnapshot(
            is_recording=False, filename=filename, started_at=None, elapsed_seconds=elapsed
        )

    def get_recording_status(self) -> RecordingStatusSnapshot:
        elapsed = (
            time.monotonic() - self._record_started if self._record_started is not None else None
        )
        return RecordingStatusSnapshot(
            is_recording=self._recording,
            filename=self._record_filename,
            started_at=self._record_started,
            elapsed_seconds=elapsed,
        )


class FakePTZController:
    """Stands in for PTZController in tests: no real pytapo/Tapo client, no
    real network calls -- just enough state to exercise the ptz router.
    """

    def __init__(self) -> None:
        self._pan = 0.0
        self._tilt = 0.0
        self.moves: list[tuple[float, float]] = []
        self.nudges: list[float] = []
        self.calibrations = 0

    def move_to(self, pan: float, tilt: float) -> PTZStatus:
        self.moves.append((pan, tilt))
        self._pan = pan
        self._tilt = tilt
        return PTZStatus(pan=self._pan, tilt=self._tilt)

    def nudge(self, direction_deg: float) -> None:
        if not (0 <= direction_deg < 360):
            raise ValueError("direction must satisfy 0 <= direction < 360")
        self.nudges.append(direction_deg)

    def calibrate(self) -> PTZStatus:
        self.calibrations += 1
        self._pan = 0.0
        self._tilt = 0.0
        return PTZStatus(pan=self._pan, tilt=self._tilt)

    def status(self) -> PTZStatus:
        return PTZStatus(pan=self._pan, tilt=self._tilt)
