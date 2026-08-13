import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Cat(Base):
    """A persistent identity produced by the detector.

    `track_id`/`camera_id` reflect the most recently observed
    CentroidTracker track -- NOT the identity itself. Identity is resolved
    by appearance (see `embedding`, app.vision.reid, and
    CatService.identify_or_create): a track_id is just an in-memory,
    per-process counter that CentroidTracker reassigns from 1 on every
    restart and reuses once an old track ages out, so two different
    physical cats can legitimately share the same track_id at different
    times. `embedding` is a running-average appearance descriptor
    (currently an HSV color histogram, see app.vision.reid.compute_embedding)
    that lets a cat keep the same Cat.id across process restarts and across
    the tracker briefly losing and reacquiring it -- that's what makes the
    identity "persistent" rather than resetting with every new track_id.

    This is deliberately separate from the manual cat registry in
    ``registered_cats``. The detector may observe an unknown cat; a human
    creates a registered profile only when its identity is known.
    """

    __tablename__ = "detected_cats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[str] = mapped_column(index=True)
    track_id: Mapped[int] = mapped_column(index=True)
    label: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    # Set when the appearance of this detector identity matches a manually
    # registered cat reference image. Tracking rows still point here, never
    # directly to the human-managed registry.
    registered_cat_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registered_cats.id"), nullable=True, index=True
    )
    # Running-average appearance descriptor for re-identification -- a JSON
    # list[float] (see app.vision.reid), or NULL until the first embeddable
    # observation. `embedding_samples` is how many observations have been
    # blended in so far, capped by app.vision.reid.running_average's
    # max_samples so the average stays adaptable instead of freezing solid.
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    embedding_samples: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
