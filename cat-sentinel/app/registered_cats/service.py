from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.registered_cats.models import RegisteredCat
from app.registered_cats.repository import RegisteredCatRepository
from app.registered_cats.schemas import RegisteredCatCreate, RegisteredCatUpdate
from app.settings.config import settings
from app.vision.reid import cosine_similarity


class RegisteredCatService:
    def __init__(self, repository: RegisteredCatRepository):
        self.repository = repository

    async def create(self, payload: RegisteredCatCreate) -> RegisteredCat:
        return await self.repository.create(payload)

    async def get(self, cat_id: uuid.UUID) -> RegisteredCat:
        cat = await self.repository.get(cat_id)
        if cat is None:
            raise NotFoundError(f"Registered cat {cat_id} not found")
        return cat

    async def list(self, limit: int, offset: int) -> list[RegisteredCat]:
        return await self.repository.list(limit, offset)

    async def update(self, cat_id: uuid.UUID, payload: RegisteredCatUpdate) -> RegisteredCat:
        return await self.repository.update(await self.get(cat_id), payload)

    async def set_photo_path(self, cat_id: uuid.UUID, photo_path: str) -> RegisteredCat:
        return await self.repository.set_photo_path(await self.get(cat_id), photo_path)

    async def add_reference_image(
        self, cat_id: uuid.UUID, image_path: str, embedding: list[float] | None
    ) -> RegisteredCat:
        return await self.repository.add_reference_image(
            await self.get(cat_id), image_path, embedding
        )

    async def find_best_match(self, embedding: list[float] | None) -> RegisteredCat | None:
        if embedding is None:
            return None
        best_cat: RegisteredCat | None = None
        best_score = -1.0
        for cat, reference in await self.repository.list_reference_embeddings():
            score = cosine_similarity(reference.embedding or [], embedding)
            if score > best_score:
                best_score = score
                best_cat = cat
        if best_score >= settings.reid_similarity_threshold:
            return best_cat
        return None
