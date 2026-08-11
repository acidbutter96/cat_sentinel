from __future__ import annotations

from pydantic import BaseModel


class CameraStatusResponse(BaseModel):
    connected: bool
    transport: str
    last_error: str | None
    frame_age_seconds: float | None


class RecordingStartResponse(BaseModel):
    filename: str
    started: bool


class RecordingStopResponse(BaseModel):
    filename: str
    elapsed_seconds: float
    stopped: bool


class RecordingLiveStatusResponse(BaseModel):
    is_recording: bool
    filename: str | None
    elapsed_seconds: float | None


class ResetResponse(BaseModel):
    reset: bool
