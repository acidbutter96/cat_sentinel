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
    bounding_box: BoundingBox
    captured_at: datetime
    age_seconds: float
