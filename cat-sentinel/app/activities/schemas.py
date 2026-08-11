import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.activities.models import ActivityKind


class ActivityCreate(BaseModel):
    camera_id: str
    cat_id: uuid.UUID | None = None
    kind: ActivityKind
    message: str


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: str
    cat_id: uuid.UUID | None
    kind: ActivityKind
    message: str
    created_at: datetime
