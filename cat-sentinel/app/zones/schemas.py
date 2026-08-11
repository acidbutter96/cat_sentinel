import math
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

MIN_POINTS = 3
MAX_POINTS = 200


class Point(BaseModel):
    x: float
    y: float

    @field_validator("x", "y")
    @classmethod
    def reject_non_finite(cls, value: float) -> float:
        if math.isinf(value) or math.isnan(value):
            raise ValueError("coordinate must be a finite number")
        return value


class ZoneCreate(BaseModel):
    camera_id: str
    name: str
    points: list[Point]
    is_active: bool = True

    @field_validator("points")
    @classmethod
    def validate_point_count(cls, value: list[Point]) -> list[Point]:
        if len(value) < MIN_POINTS:
            raise ValueError(f"a zone polygon needs at least {MIN_POINTS} points")
        if len(value) > MAX_POINTS:
            raise ValueError(f"a zone polygon may have at most {MAX_POINTS} points")
        return value


class ZoneUpdate(BaseModel):
    name: str | None = None
    points: list[Point] | None = None
    is_active: bool | None = None

    @field_validator("points")
    @classmethod
    def validate_point_count(cls, value: list[Point] | None) -> list[Point] | None:
        if value is None:
            return value
        if len(value) < MIN_POINTS:
            raise ValueError(f"a zone polygon needs at least {MIN_POINTS} points")
        if len(value) > MAX_POINTS:
            raise ValueError(f"a zone polygon may have at most {MAX_POINTS} points")
        return value


class ZoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: str
    name: str
    points: list[Point]
    is_active: bool
    created_at: datetime
    updated_at: datetime
