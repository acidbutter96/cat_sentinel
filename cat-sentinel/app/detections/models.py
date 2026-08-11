import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Detection(Base):
    """A single per-frame observation of a tracked cat."""

    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cats.id"), index=True)
    camera_id: Mapped[str] = mapped_column(index=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    # [x1, y1, x2, y2]
    bbox: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    # {"x": float, "y": float}
    centroid: Mapped[dict] = mapped_column(JSON, nullable=False)
    in_danger_zone: Mapped[bool] = mapped_column(default=False, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
