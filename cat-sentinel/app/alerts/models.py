import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class AlertKind(str, enum.Enum):
    DANGER_ZONE = "danger_zone"  # a cat entered a defined danger zone
    CAMERA_ENTRY = "camera_entry"  # a cat entered the camera's field of view


class Alert(Base):
    """A fired alert and its outbound-webhook delivery status.

    `zone_id` is only set for AlertKind.DANGER_ZONE alerts -- CAMERA_ENTRY
    alerts (a cat simply appeared on camera, see
    app.detections.pipeline.DetectionPipeline) have no associated zone.
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("detected_cats.id"), index=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("zones.id"), nullable=True, index=True
    )
    kind: Mapped[AlertKind] = mapped_column(
        Enum(AlertKind, native_enum=False), default=AlertKind.DANGER_ZONE, index=True
    )
    camera_id: Mapped[str] = mapped_column(index=True)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, native_enum=False), default=AlertStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
