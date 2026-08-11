from __future__ import annotations

from app.activities.models import Activity
from app.activities.repository import ActivityRepository
from app.activities.schemas import ActivityCreate
from app.core.decorators import log_errors


@log_errors
class ActivityService:
    def __init__(self, repository: ActivityRepository):
        self.repository = repository

    async def record(self, payload: ActivityCreate) -> Activity:
        return await self.repository.create(payload)

    async def list(self, limit: int = 50, offset: int = 0) -> list[Activity]:
        return await self.repository.list(limit=limit, offset=offset)
