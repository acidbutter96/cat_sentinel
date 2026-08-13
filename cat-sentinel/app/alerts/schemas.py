import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.alerts.models import AlertKind, AlertStatus


class AlertCreate(BaseModel):
    cat_id: uuid.UUID
    zone_id: uuid.UUID | None = None
    camera_id: str
    kind: AlertKind = AlertKind.DANGER_ZONE
    status: AlertStatus = AlertStatus.PENDING
    error_message: str | None = None


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cat_id: uuid.UUID
    zone_id: uuid.UUID | None
    camera_id: str
    kind: AlertKind
    status: AlertStatus
    error_message: str | None
    created_at: datetime
