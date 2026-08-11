from __future__ import annotations

import uuid

from app.core.decorators import log_errors
from app.detections.models import Detection
from app.detections.repository import DetectionRepository
from app.detections.schemas import DetectionCreate


@log_errors
class DetectionService:
    def __init__(self, repository: DetectionRepository):
        self.repository = repository

    async def create(self, payload: DetectionCreate) -> Detection:
        return await self.repository.create(payload)

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        cat_id: uuid.UUID | None = None,
        in_danger_zone: bool | None = None,
    ) -> list[Detection]:
        return await self.repository.list(
            limit=limit, offset=offset, cat_id=cat_id, in_danger_zone=in_danger_zone
        )
