from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert, AlertStatus
from app.alerts.schemas import AlertCreate


class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: AlertCreate) -> Alert:
        alert = Alert(
            cat_id=payload.cat_id,
            zone_id=payload.zone_id,
            camera_id=payload.camera_id,
            status=payload.status,
            error_message=payload.error_message,
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def mark_status(
        self, alert: Alert, status: AlertStatus, error_message: str | None = None
    ) -> Alert:
        alert.status = status
        alert.error_message = error_message
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def list(self, limit: int = 50, offset: int = 0) -> list[Alert]:
        stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, alert_id: uuid.UUID) -> Alert | None:
        return await self.session.get(Alert, alert_id)
