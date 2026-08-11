from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.activities.models import Activity
from app.activities.schemas import ActivityCreate


class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: ActivityCreate) -> Activity:
        activity = Activity(
            camera_id=payload.camera_id,
            cat_id=payload.cat_id,
            kind=payload.kind,
            message=payload.message,
        )
        self.session.add(activity)
        await self.session.commit()
        await self.session.refresh(activity)
        return activity

    async def list(self, limit: int = 50, offset: int = 0) -> list[Activity]:
        stmt = select(Activity).order_by(Activity.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
