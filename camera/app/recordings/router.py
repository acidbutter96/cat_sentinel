from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.dependencies import DbSession
from app.recordings.repository import RecordingRepository
from app.recordings.schemas import RecordingRead
from app.recordings.service import RecordingService

router = APIRouter(prefix="/recordings", tags=["recordings"])


def get_recording_service(db: DbSession) -> RecordingService:
    return RecordingService(RecordingRepository(db))


RecordingServiceDep = Annotated[RecordingService, Depends(get_recording_service)]


@router.get("", response_model=list[RecordingRead], summary="List recordings")
async def list_recordings(service: RecordingServiceDep) -> list[RecordingRead]:
    return await service.list_all()


@router.get(
    "/{filename}",
    summary="Download a recording file",
    response_class=FileResponse,
)
async def download_recording(filename: str, service: RecordingServiceDep) -> FileResponse:
    path = await service.get_file_path(filename)
    return FileResponse(path, media_type="video/mp4", filename=filename)
