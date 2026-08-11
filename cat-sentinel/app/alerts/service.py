from __future__ import annotations

import time
import uuid

import httpx

from app.alerts.models import Alert, AlertStatus
from app.alerts.repository import AlertRepository
from app.alerts.schemas import AlertCreate
from app.core.decorators import log_errors
from app.settings.config import settings


class AlertCooldownTracker:
    """Tracks the last time an alert fired for a given (cat_id, zone_id) pair
    so the pipeline doesn't spam a webhook every frame a cat lingers in a
    danger zone. Pure in-memory state -- process-local, not shared across
    workers, which is fine for this service's single-pipeline-process model.
    """

    def __init__(self, cooldown_seconds: float | None = None):
        self.cooldown_seconds = (
            cooldown_seconds if cooldown_seconds is not None else settings.alert_cooldown_seconds
        )
        self._last_fired: dict[tuple[uuid.UUID, uuid.UUID], float] = {}

    def should_fire(self, cat_id: uuid.UUID, zone_id: uuid.UUID) -> bool:
        key = (cat_id, zone_id)
        last = self._last_fired.get(key)
        if last is None:
            return True
        return (time.monotonic() - last) >= self.cooldown_seconds

    def mark_fired(self, cat_id: uuid.UUID, zone_id: uuid.UUID) -> None:
        self._last_fired[(cat_id, zone_id)] = time.monotonic()


@log_errors
class AlertService:
    def __init__(self, repository: AlertRepository, webhook_url: str | None = None):
        self.repository = repository
        self.webhook_url = webhook_url if webhook_url is not None else settings.alert_webhook_url

    async def list(self, limit: int = 50, offset: int = 0) -> list[Alert]:
        return await self.repository.list(limit=limit, offset=offset)

    async def fire(self, cat_id: uuid.UUID, zone_id: uuid.UUID, camera_id: str) -> Alert:
        """Records a pending alert, POSTs the webhook, and updates the alert's
        delivery status based on the outcome.
        """
        alert = await self.repository.create(
            AlertCreate(
                cat_id=cat_id, zone_id=zone_id, camera_id=camera_id, status=AlertStatus.PENDING
            )
        )
        payload = {
            "cat_id": str(cat_id),
            "zone_id": str(zone_id),
            "camera_id": camera_id,
            "event": "cat_entered_danger_zone",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return await self.repository.mark_status(alert, AlertStatus.FAILED, str(exc))
        return await self.repository.mark_status(alert, AlertStatus.SENT)
