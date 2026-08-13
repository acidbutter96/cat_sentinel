import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CatSex(str, enum.Enum):
    FEMALE = "female"
    MALE = "male"
    UNKNOWN = "unknown"


class RegisteredCat(Base):
    """Human-maintained profile for a known cat.

    ``detected_cat_id`` is optional: cats may be registered before the camera
    recognizes them, then linked to their detector identity later.
    """

    __tablename__ = "registered_cats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    detected_cat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("detected_cats.id"), unique=True, nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[CatSex] = mapped_column(
        Enum(CatSex, native_enum=False), default=CatSex.UNKNOWN, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RegisteredCatReferenceImage(Base):
    """An image supplied by a person to recognize a registered cat."""

    __tablename__ = "registered_cat_reference_images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    registered_cat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registered_cats.id"), index=True, nullable=False
    )
    image_path: Mapped[str] = mapped_column(unique=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
