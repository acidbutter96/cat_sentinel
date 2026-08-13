from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.detections.models import Detection
from app.detections.schemas import DetectionCreate


class DetectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: DetectionCreate) -> Detection:
        detection = Detection(
            cat_id=payload.cat_id,
            camera_id=payload.camera_id,
            track_id=payload.track_id,
            zone_id=payload.zone_id,
            bbox=payload.bbox,
            centroid=payload.centroid.model_dump(),
            in_danger_zone=payload.in_danger_zone,
            confidence=payload.confidence,
            snapshot_path=payload.snapshot_path,
            frame_path=payload.frame_path,
        )
        if payload.timestamp is not None:
            detection.timestamp = payload.timestamp
        self.session.add(detection)
        await self.session.commit()
        await self.session.refresh(detection)
        return detection

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        cat_id: uuid.UUID | None = None,
        in_danger_zone: bool | None = None,
    ) -> list[Detection]:
        stmt = select(Detection).order_by(Detection.timestamp.desc())
        if cat_id is not None:
            stmt = stmt.where(Detection.cat_id == cat_id)
        if in_danger_zone is not None:
            stmt = stmt.where(Detection.in_danger_zone == in_danger_zone)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
