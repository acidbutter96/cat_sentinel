import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Detection(Base):
    """A single per-frame observation of a tracked cat."""

    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("detected_cats.id"), index=True)
    camera_id: Mapped[str] = mapped_column(index=True)
    # Tracker-local identifier at the instant this frame was processed.
    track_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    # [x1, y1, x2, y2]
    bbox: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    # {"x": float, "y": float}
    centroid: Mapped[dict] = mapped_column(JSON, nullable=False)
    in_danger_zone: Mapped[bool] = mapped_column(default=False, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    # Relative path to the cat crop captured when this track first appeared.
    snapshot_path: Mapped[str | None] = mapped_column(nullable=True)
    # Relative path to the full source frame captured with snapshot_path.
    frame_path: Mapped[str | None] = mapped_column(nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
