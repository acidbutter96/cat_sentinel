from __future__ import annotations

import uuid

from app.cats.models import Cat
from app.cats.repository import CatRepository
from app.cats.schemas import CatUpdate
from app.core.decorators import log_errors
from app.core.exceptions import NotFoundError


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
        return await self.repository.get_or_create(camera_id, track_id)

    async def update(self, cat_id: uuid.UUID, payload: CatUpdate) -> Cat:
        cat = await self.get(cat_id)
        return await self.repository.update(cat, payload)
