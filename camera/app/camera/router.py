"""Router for the camera bridge itself: live viewer page, MJPEG stream,
snapshot, status, reset, and start/stop/status of recording (which reuses
this same RTSPCamera's decode buffer -- see app/camera/service.py).

Mounted at the app root (no prefix): GET /, GET /video, GET /snapshot, etc.
match the spec exactly. Recording *metadata* (list/download, DB-backed)
lives under app/recordings/ at its own /recordings prefix.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.camera.schemas import (
    CameraStatusResponse,
    RecordingLiveStatusResponse,
    RecordingStartResponse,
    RecordingStopResponse,
    ResetResponse,
)
from app.camera.service import RTSPCamera
from app.core.dependencies import CameraDep, DbSession
from app.core.exceptions import FrameNotAvailableError, RecordingAlreadyInProgressError
from app.recordings.repository import RecordingRepository
from app.recordings.service import RecordingService, generate_filename, recordings_dir

router = APIRouter(tags=["camera"])

_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

MJPEG_BOUNDARY = "frame"
STREAM_POLL_INTERVAL_SECONDS = 0.05


@router.get("/", response_class=HTMLResponse, summary="Live viewer page")
async def viewer(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "viewer.html")


async def _mjpeg_generator(camera: RTSPCamera):
    """Async generator yielding multipart MJPEG chunks. Stops when the
    client disconnects (handled by StreamingResponse itself when the
    generator raises/returns) or when camera.is_running() goes false.
    """
    last_sent: bytes | None = None
    while camera.is_running():
        frame = camera.get_frame()
        if frame is not None and frame != last_sent:
            last_sent = frame
            yield (
                b"--" + MJPEG_BOUNDARY.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
            )
        await asyncio.sleep(STREAM_POLL_INTERVAL_SECONDS)


@router.get("/video", summary="MJPEG live video stream")
async def video(camera: CameraDep) -> StreamingResponse:
    return StreamingResponse(
        _mjpeg_generator(camera),
        media_type=f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}",
    )


@router.get("/snapshot", summary="Latest decoded JPEG frame")
async def snapshot(camera: CameraDep) -> Response:
    frame = camera.get_frame()
    if frame is None:
        raise FrameNotAvailableError()
    return Response(content=frame, media_type="image/jpeg")


@router.get("/status", response_model=CameraStatusResponse, summary="Camera connection status")
async def status_(camera: CameraDep) -> CameraStatusResponse:
    snap = camera.get_status()
    return CameraStatusResponse(
        connected=snap.connected,
        transport=snap.transport,
        last_error=snap.last_error,
        frame_age_seconds=snap.frame_age_seconds,
    )


@router.post("/reset", response_model=ResetResponse, summary="Force camera teardown and reconnect")
async def reset(camera: CameraDep) -> ResetResponse:
    camera.reset()
    return ResetResponse(reset=True)


def get_recording_service(db: DbSession) -> RecordingService:
    return RecordingService(RecordingRepository(db))


RecordingServiceDep = Annotated[RecordingService, Depends(get_recording_service)]


@router.post(
    "/recording/start",
    response_model=RecordingStartResponse,
    summary="Start writing the live decode buffer to a video file",
)
async def start_recording(
    camera: CameraDep, recording_service: RecordingServiceDep
) -> RecordingStartResponse:
    live_status = camera.get_recording_status()
    if live_status.is_recording:
        raise RecordingAlreadyInProgressError()

    filename = generate_filename()
    try:
        camera.start_recording(filename, recordings_dir())
    except RuntimeError as exc:
        raise RecordingAlreadyInProgressError(str(exc)) from exc

    await recording_service.start(filename)
    return RecordingStartResponse(filename=filename, started=True)


@router.post(
    "/recording/stop",
    response_model=RecordingStopResponse,
    summary="Stop the active recording",
)
async def stop_recording(
    camera: CameraDep, recording_service: RecordingServiceDep
) -> RecordingStopResponse:
    snap = camera.stop_recording()
    await recording_service.stop(snap.filename)
    return RecordingStopResponse(
        filename=snap.filename, elapsed_seconds=snap.elapsed_seconds or 0.0, stopped=True
    )


@router.get(
    "/recording/status",
    response_model=RecordingLiveStatusResponse,
    summary="Whether a recording is currently in progress",
)
async def recording_status(camera: CameraDep) -> RecordingLiveStatusResponse:
    snap = camera.get_recording_status()
    return RecordingLiveStatusResponse(
        is_recording=snap.is_recording,
        filename=snap.filename,
        elapsed_seconds=snap.elapsed_seconds,
    )
