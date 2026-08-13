import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CatCreate(BaseModel):
    camera_id: str
    track_id: int
    label: str | None = None
    is_active: bool = True


class CatUpdate(BaseModel):
    label: str | None = None
    is_active: bool | None = None


class CatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: str
    track_id: int
    label: str
    is_active: bool
    registered_cat_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
