from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cats.models import Cat
from app.cats.schemas import CatUpdate
from app.core.exceptions import ConflictError


class CatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, cat_id: uuid.UUID) -> Cat | None:
        return await self.session.get(Cat, cat_id)

    async def get_by_track_id(self, camera_id: str, track_id: int) -> Cat | None:
        result = await self.session.execute(
            select(Cat).where(Cat.camera_id == camera_id, Cat.track_id == track_id)
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> list[Cat]:
        result = await self.session.execute(select(Cat).limit(limit).offset(offset))
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
