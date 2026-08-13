from __future__ import annotations

import uuid

from app.cats.models import Cat
from app.cats.repository import CatRepository
from app.cats.schemas import CatUpdate
from app.core.decorators import log_errors
from app.core.exceptions import NotFoundError
from app.settings.config import settings
from app.vision.reid import cosine_similarity


@log_errors
class CatService:
    def __init__(self, repository: CatRepository):
        self.repository = repository

    async def get(self, cat_id: uuid.UUID) -> Cat:
        cat = await self.repository.get(cat_id)
        if cat is None:
            raise NotFoundError(f"Cat {cat_id} not found")
        return cat

    async def list(self, limit: int = 50, offset: int = 0) -> list[Cat]:
        return await self.repository.list(limit=limit, offset=offset)

    async def get_or_create_for_track(self, camera_id: str, track_id: int) -> Cat:
        """Track-id-only resolution -- kept for callers with no frame/crop
        to derive an appearance embedding from. Prefer identify_or_create
        when an embedding is available: this path can't tell two different
        physical cats apart if they end up sharing a reused track_id.
        """
        return await self.repository.get_or_create(camera_id, track_id)

    async def identify_or_create(
        self,
        camera_id: str,
        track_id: int,
        embedding: list[float] | None,
        registered_cat_id: uuid.UUID | None = None,
        registered_cat_name: str | None = None,
    ) -> Cat:
        """Resolves a per-frame tracker observation to a persistent Cat
        identity by appearance, not by track_id.

        track_id is an in-memory CentroidTracker counter that resets to 1 on
        every process restart and gets reassigned once an old track ages
        out (see the Cat model docstring) -- matching on it alone would
        silently create a new "duplicate" cat identity every time the
        pipeline restarts or a cat leaves and re-enters frame. Instead, this
        compares `embedding` against every active, previously-embedded cat
        on this camera and reuses the best match above
        settings.reid_similarity_threshold; only creates a new Cat when
        nothing matches closely enough (a genuinely new cat, or the very
        first observation ever).

        Falls back to get_or_create_for_track when no embedding could be
        extracted for this observation (e.g. a degenerate crop).
        """
        if embedding is None:
            return await self.get_or_create_for_track(camera_id, track_id)

        candidates = await self.repository.list_active_with_embedding(camera_id)
        best_cat: Cat | None = None
        best_score = -1.0
        for candidate in candidates:
            score = cosine_similarity(candidate.embedding or [], embedding)
            if score > best_score:
                best_score = score
                best_cat = candidate

        if best_cat is not None and best_score >= settings.reid_similarity_threshold:
            return await self.repository.update_identity(
                best_cat,
                track_id,
                camera_id,
                embedding,
                registered_cat_id,
                registered_cat_name,
            )

        return await self.repository.create_with_embedding(
            camera_id,
            track_id,
            embedding,
            registered_cat_id,
            registered_cat_name,
        )

    async def touch(self, cat_id: uuid.UUID, embedding: list[float] | None) -> Cat:
        """Refreshes a cat's running-average embedding for a track_id that's
        already been resolved earlier in this pipeline run (see
        DetectionPipeline's per-track cache) -- cheaper than re-running
        identify_or_create's full candidate search on every single frame.
        """
        cat = await self.get(cat_id)
        if embedding is None:
            return cat
        return await self.repository.update_identity(cat, cat.track_id, cat.camera_id, embedding)

    async def update(self, cat_id: uuid.UUID, payload: CatUpdate) -> Cat:
        cat = await self.get(cat_id)
        return await self.repository.update(cat, payload)
