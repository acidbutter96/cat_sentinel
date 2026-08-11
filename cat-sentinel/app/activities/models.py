import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityKind(str, enum.Enum):
    DETECTION = "detection"
    ALERT = "alert"


class Activity(Base):
    """A simple aggregated timeline entry, populated alongside detection and
    alert creation (see app.detections.pipeline.DetectionPipeline).
    """

    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[str] = mapped_column(index=True)
    cat_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    kind: Mapped[ActivityKind] = mapped_column(Enum(ActivityKind, native_enum=False), index=True)
    message: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
