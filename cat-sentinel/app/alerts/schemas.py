import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.alerts.models import AlertStatus


class AlertCreate(BaseModel):
    cat_id: uuid.UUID
    zone_id: uuid.UUID
    camera_id: str
    status: AlertStatus = AlertStatus.PENDING
    error_message: str | None = None


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cat_id: uuid.UUID
    zone_id: uuid.UUID
    camera_id: str
    status: AlertStatus
    error_message: str | None
    created_at: datetime
