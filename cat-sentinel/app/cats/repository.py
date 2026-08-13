from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cats.models import Cat
from app.cats.schemas import CatUpdate
from app.core.exceptions import ConflictError
from app.vision.reid import running_average


class CatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, cat_id: uuid.UUID) -> Cat | None:
        return await self.session.get(Cat, cat_id)

    async def get_by_track_id(self, camera_id: str, track_id: int) -> Cat | None:
        """Best-effort fallback lookup used only when no appearance
        embedding is available (see CatService.identify_or_create). Since
        track_id is reused across different physical cats over time (see
        the Cat model docstring), more than one row can share a
        (camera_id, track_id) pair -- pick the most recently updated one
        rather than raising on multiple results.
        """
        result = await self.session.execute(
            select(Cat)
            .where(Cat.camera_id == camera_id, Cat.track_id == track_id)
            .order_by(Cat.updated_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def list(self, limit: int = 50, offset: int = 0) -> list[Cat]:
        result = await self.session.execute(select(Cat).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def list_active_with_embedding(self, camera_id: str) -> list[Cat]:
        """Candidates for appearance-based re-identification: active cats on
        this camera that have at least one prior embedding observation.
        """
        result = await self.session.execute(
            select(Cat).where(
                Cat.camera_id == camera_id,
                Cat.is_active.is_(True),
                Cat.embedding.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def get_or_create(self, camera_id: str, track_id: int) -> Cat:
        existing = await self.get_by_track_id(camera_id, track_id)
        if existing is not None:
            return existing
        cat = Cat(camera_id=camera_id, track_id=track_id, label=f"cat #{track_id}", is_active=True)
        self.session.add(cat)
        try:
            await self.session.commit()
        except IntegrityError:
            # Lost a race with another writer creating the same track ID --
            # roll back and fetch the row that won.
            await self.session.rollback()
            existing = await self.get_by_track_id(camera_id, track_id)
            if existing is not None:
                return existing
            raise
        await self.session.refresh(cat)
        return cat

    async def create_with_embedding(
        self,
        camera_id: str,
        track_id: int,
        embedding: list[float],
        registered_cat_id: uuid.UUID | None = None,
        label: str | None = None,
    ) -> Cat:
        cat = Cat(
            camera_id=camera_id,
            track_id=track_id,
            label=label or f"cat #{track_id}",
            is_active=True,
            embedding=embedding,
            embedding_samples=1,
            registered_cat_id=registered_cat_id,
        )
        self.session.add(cat)
        await self.session.commit()
        await self.session.refresh(cat)
        return cat

    async def update_identity(
        self,
        cat: Cat,
        track_id: int,
        camera_id: str,
        embedding: list[float] | None,
        registered_cat_id: uuid.UUID | None = None,
        label: str | None = None,
    ) -> Cat:
        """Re-associates `cat` with the latest observed track_id/camera_id
        and, if an embedding was extracted for this observation, blends it
        into the cat's running-average appearance descriptor.
        """
        cat.track_id = track_id
        cat.camera_id = camera_id
        if cat.registered_cat_id is None and registered_cat_id is not None:
            cat.registered_cat_id = registered_cat_id
            if label is not None and cat.label.startswith("cat #"):
                cat.label = label
        if embedding is not None:
            if cat.embedding and cat.embedding_samples:
                cat.embedding = running_average(cat.embedding, cat.embedding_samples, embedding)
                cat.embedding_samples += 1
            else:
                cat.embedding = embedding
                cat.embedding_samples = 1
        await self.session.commit()
        await self.session.refresh(cat)
        return cat

    async def update(self, cat: Cat, payload: CatUpdate) -> Cat:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(cat, field, value)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(f"Cat {cat.id} could not be updated") from exc
        await self.session.refresh(cat)
        return cat
