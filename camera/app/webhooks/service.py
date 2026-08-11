"""Outbound event notification subscriptions -- the "out" half of the event
pipeline (app/events/ is the "in" half). In-memory storage, consistent with
how app.events.service keeps its command-mapping table in-memory: this
domain doesn't need durability either, and keeping both simple avoids mixing
DB-backed and in-memory patterns for two very similar small tables.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import httpx

from app.core.decorators import log_call
from app.core.exceptions import NotFoundError
from app.settings.config import settings
from app.webhooks.schemas import WebhookSubscriptionCreate, WebhookSubscriptionRead

if TYPE_CHECKING:
    from app.events.schemas import EventTrigger

logger = logging.getLogger(__name__)


class _Subscription:
    __slots__ = ("id", "url", "event_types")

    def __init__(self, id_: uuid.UUID, url: str, event_types: list[str] | None):
        self.id = id_
        self.url = url
        self.event_types = event_types


class WebhookService:
    """Not @log_errors as a whole: notify_all() fans out over the network on
    the hot path of every event trigger and has its own per-subscriber
    logging (one line per failure) rather than one entry/error line for the
    whole batch -- see notify_all below.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[uuid.UUID, _Subscription] = {}

    @log_call
    async def create(self, payload: WebhookSubscriptionCreate) -> WebhookSubscriptionRead:
        sub_id = uuid.uuid4()
        sub = _Subscription(sub_id, str(payload.url), payload.event_types)
        self._subscriptions[sub_id] = sub
        return WebhookSubscriptionRead(id=sub_id, url=sub.url, event_types=sub.event_types)

    @log_call
    async def list_all(self) -> list[WebhookSubscriptionRead]:
        return [
            WebhookSubscriptionRead(id=s.id, url=s.url, event_types=s.event_types)
            for s in self._subscriptions.values()
        ]

    @log_call
    async def delete(self, webhook_id: uuid.UUID) -> None:
        if webhook_id not in self._subscriptions:
            raise NotFoundError(f"No webhook subscription with id={webhook_id}")
        del self._subscriptions[webhook_id]

    async def notify_all(self, trigger: EventTrigger) -> int:
        """Best-effort fan-out: POST to every matching subscriber with a
        short timeout, swallow failures (log them), never let a webhook
        failure propagate -- the caller (EventIngestionService) also wraps
        this in a try/except as defense in depth, but this method already
        guarantees it never raises for an individual subscriber's failure.
        """
        matching = [
            s
            for s in self._subscriptions.values()
            if s.event_types is None or trigger.event_type in s.event_types
        ]
        if not matching:
            return 0

        payload = {
            "event_type": trigger.event_type,
            "camera_id": trigger.camera_id,
            "metadata": trigger.metadata,
            "timestamp": trigger.timestamp.isoformat(),
        }

        notified = 0
        async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
            for sub in matching:
                try:
                    response = await client.post(sub.url, json=payload)
                    response.raise_for_status()
                    notified += 1
                except Exception as exc:  # noqa: BLE001 -- deliberate: never let one subscriber's failure stop the rest
                    logger.warning("webhook delivery to %s failed: %s", sub.url, exc)
        return notified
