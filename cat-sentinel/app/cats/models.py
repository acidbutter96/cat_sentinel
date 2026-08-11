import uuid
from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Cat(Base):
    """A tracked cat identity, auto-created the first time a track ID is
    seen on a given camera. `label` defaults to "cat #<track_id>" and can be
    overridden by a human (e.g. "Whiskers"). `is_active` retires an identity
    without deleting its detection history.
    """

    __tablename__ = "cats"
    __table_args__ = (UniqueConstraint("camera_id", "track_id", name="uq_cats_camera_id_track_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[str] = mapped_column(index=True)
    track_id: Mapped[int] = mapped_column(index=True)
    label: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
