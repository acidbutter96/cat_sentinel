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


class Alert(Base):
    """A fired danger-zone alert and its outbound-webhook delivery status."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cats.id"), index=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("zones.id"), index=True)
    camera_id: Mapped[str] = mapped_column(index=True)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, native_enum=False), default=AlertStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
