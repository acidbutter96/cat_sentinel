from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.recordings.models import RecordingStatus


class RecordingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float | None
    file_size_bytes: int | None
    status: RecordingStatus


class RecordingStartResponse(BaseModel):
    filename: str
    started_at: datetime


class RecordingStopResponse(BaseModel):
    filename: str
    ended_at: datetime
    duration_seconds: float


class RecordingLiveStatus(BaseModel):
    is_recording: bool
    filename: str | None
    started_at: datetime | None
    elapsed_seconds: float | None
