"""Keeps a recording continuously running against the shared RTSPCamera,
split into fixed-duration chunk files (settings.recording_chunk_seconds,
default 1h) instead of one ever-growing video -- so a long-running deployment
doesn't end up with a single multi-gigabyte file, and so each chunk's
recordings-table row (started_at/ended_at) makes it possible to look up
"which chunk covers this timestamp" later (see app.recordings.models).

This is deliberately self-healing: on every check, if recording_auto_start
is set and nothing is currently recording (first boot, or a previous chunk
failed to roll over cleanly), it starts a new chunk rather than requiring a
human to notice and hit POST /recording/start again. Manual
POST /recording/start /stop via app.camera.router still work as before --
starting one manually just becomes the currently-open chunk, and stopping
one manually leaves recording off until the next check tick restarts it
(if auto_start is enabled).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from app.camera.service import RTSPCamera
from app.recordings.repository import RecordingRepository
from app.recordings.service import RecordingService, generate_filename, recordings_dir

logger = logging.getLogger(__name__)

CHUNK_CHECK_INTERVAL_SECONDS = 5.0


async def _start_new_chunk(camera: RTSPCamera, recording_service: RecordingService) -> None:
    filename = generate_filename()
    await recording_service.start(filename)
    try:
        camera.start_recording(filename, recordings_dir())
    except Exception:
        with contextlib.suppress(Exception):
            await recording_service.fail(filename)
        raise
    logger.info("recording chunk started: %s", filename)


async def _stop_current_chunk(camera: RTSPCamera, recording_service: RecordingService) -> None:
    snap = camera.stop_recording()
    if snap.filename is not None:
        await recording_service.stop(snap.filename)
        logger.info(
            "recording chunk closed: %s (%.1fs)", snap.filename, snap.elapsed_seconds or 0.0
        )


async def run_recording_chunk_tick(
    camera: RTSPCamera,
    session_factory,
    chunk_seconds: int,
    auto_start: bool,
) -> None:
    """One decision cycle, isolated from the sleep loop below so it's
    directly unit-testable without waiting on real wall-clock time (see
    tests/test_recording_chunking.py).
    """
    status = camera.get_recording_status()

    if not status.is_recording:
        if auto_start:
            async with session_factory() as session:
                recording_service = RecordingService(RecordingRepository(session))
                try:
                    await recording_service.fail_open_recordings()
                    await _start_new_chunk(camera, recording_service)
                except Exception:  # noqa: BLE001 -- keep auto-recording alive after transient failures
                    logger.exception("recording chunk start failed")
        return

    if status.elapsed_seconds is not None and status.elapsed_seconds >= chunk_seconds:
        async with session_factory() as session:
            recording_service = RecordingService(RecordingRepository(session))
            try:
                await _stop_current_chunk(camera, recording_service)
                await _start_new_chunk(camera, recording_service)
            except Exception:
                logger.exception("recording chunk rotation failed")


async def run_recording_chunk_loop(
    camera: RTSPCamera,
    session_factory,
    chunk_seconds: int,
    auto_start: bool,
) -> None:
    """Background asyncio task, run for the app's lifetime (see
    app.main lifespan). On cancellation (app shutdown), closes out whatever
    chunk is currently open so its file and DB row end up complete rather
    than truncated mid-write.
    """
    try:
        while True:
            await run_recording_chunk_tick(camera, session_factory, chunk_seconds, auto_start)
            await asyncio.sleep(CHUNK_CHECK_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        status = camera.get_recording_status()
        if status.is_recording:
            async with session_factory() as session:
                recording_service = RecordingService(RecordingRepository(session))
                with contextlib.suppress(Exception):
                    await _stop_current_chunk(camera, recording_service)
        raise
