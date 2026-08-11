from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.zones.models import Zone
from app.zones.schemas import ZoneCreate, ZoneUpdate


class ZoneRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: ZoneCreate) -> Zone:
        zone = Zone(
            camera_id=payload.camera_id,
            name=payload.name,
            points=[p.model_dump() for p in payload.points],
            is_active=payload.is_active,
        )
        self.session.add(zone)
        await self._commit_or_raise_conflict(payload.camera_id, payload.name)
        await self.session.refresh(zone)
        return zone

    async def get(self, zone_id: uuid.UUID) -> Zone | None:
        return await self.session.get(Zone, zone_id)

    async def list(self, limit: int = 50, offset: int = 0) -> list[Zone]:
        result = await self.session.execute(select(Zone).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def list_active_for_camera(self, camera_id: str) -> list[Zone]:
        stmt = select(Zone).where(Zone.camera_id == camera_id, Zone.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, zone: Zone, payload: ZoneUpdate) -> Zone:
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(zone, field, value)
        await self._commit_or_raise_conflict(zone.camera_id, zone.name)
        await self.session.refresh(zone)
        return zone

    async def delete(self, zone: Zone) -> None:
        await self.session.delete(zone)
        await self.session.commit()

    async def _commit_or_raise_conflict(self, camera_id: str, name: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                f"A zone named {name!r} already exists for camera {camera_id!r}"
            ) from exc
