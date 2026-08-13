from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.registered_cats.models import RegisteredCat, RegisteredCatReferenceImage
from app.registered_cats.schemas import RegisteredCatCreate, RegisteredCatUpdate


class RegisteredCatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: RegisteredCatCreate) -> RegisteredCat:
        cat = RegisteredCat(**payload.model_dump())
        self.session.add(cat)
        await self._commit(cat)
        return cat

    async def get(self, cat_id: uuid.UUID) -> RegisteredCat | None:
        return await self.session.get(RegisteredCat, cat_id)

    async def list(self, limit: int, offset: int) -> list[RegisteredCat]:
        result = await self.session.execute(
            select(RegisteredCat).order_by(RegisteredCat.name).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, cat: RegisteredCat, payload: RegisteredCatUpdate) -> RegisteredCat:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(cat, field, value)
        await self._commit(cat)
        return cat

    async def set_photo_path(self, cat: RegisteredCat, photo_path: str) -> RegisteredCat:
        cat.photo_path = photo_path
        await self._commit(cat)
        return cat

    async def add_reference_image(
        self, cat: RegisteredCat, image_path: str, embedding: list[float] | None
    ) -> RegisteredCat:
        self.session.add(
            RegisteredCatReferenceImage(
                registered_cat_id=cat.id,
                image_path=image_path,
                embedding=embedding,
            )
        )
        cat.photo_path = image_path
        await self._commit(cat)
        return cat

    async def list_reference_embeddings(
        self,
    ) -> list[tuple[RegisteredCat, RegisteredCatReferenceImage]]:
        result = await self.session.execute(
            select(RegisteredCat, RegisteredCatReferenceImage)
            .join(RegisteredCatReferenceImage)
            .where(RegisteredCatReferenceImage.embedding.is_not(None))
        )
        return list(result.all())

    async def _commit(self, cat: RegisteredCat) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Detected cat is already linked to a registered cat") from exc
        await self.session.refresh(cat)
