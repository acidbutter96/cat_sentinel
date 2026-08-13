from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class TrackerRead(BaseModel):
    """One actively-tracked cat, with its most recent bounding box/position."""

    model_config = ConfigDict(from_attributes=True)

    cat_id: str
    cat_name: str | None = None
    track_id: int | None = None
    bounding_box: BoundingBox
    captured_at: datetime
    age_seconds: float
    in_danger_zone: bool = False
    confidence: float | None = None
    snapshot_path: str | None = None
    entry_frame_path: str | None = None
    entry_track_id: int | None = None
    entry_bounding_box: BoundingBox | None = None
    entry_captured_at: datetime | None = None
