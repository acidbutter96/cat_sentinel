import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Centroid(BaseModel):
    x: float
    y: float


class DetectionCreate(BaseModel):
    cat_id: uuid.UUID
    camera_id: str
    track_id: int | None = None
    zone_id: uuid.UUID | None = None
    bbox: list[float]
    centroid: Centroid
    in_danger_zone: bool = False
    confidence: float
    snapshot_path: str | None = None
    frame_path: str | None = None
    timestamp: datetime | None = None


class DetectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cat_id: uuid.UUID
    camera_id: str
    track_id: int | None
    zone_id: uuid.UUID | None
    bbox: list[float]
    centroid: Centroid
    in_danger_zone: bool
    confidence: float
    snapshot_path: str | None
    frame_path: str | None
    timestamp: datetime
