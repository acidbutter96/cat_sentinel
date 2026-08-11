import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Zone(Base):
    """A named danger-zone polygon (list of {x, y} points) scoped to a camera."""

    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("camera_id", "name", name="uq_zones_camera_id_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str]
    # Stored as a JSON list of {"x": float, "y": float} dicts.
    points: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
