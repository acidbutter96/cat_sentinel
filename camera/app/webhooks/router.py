from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.webhooks.schemas import WebhookSubscriptionCreate, WebhookSubscriptionRead
from app.webhooks.service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Process-wide singleton: subscriptions are in-memory (see service.py
# docstring), so one shared instance -- not one per request -- is required
# for subscriptions to persist across requests.
_webhook_service = WebhookService()


def get_webhook_service() -> WebhookService:
    return _webhook_service


WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]


@router.post(
    "",
    response_model=WebhookSubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe a URL to receive a copy of every event",
)
async def create_webhook(
    payload: WebhookSubscriptionCreate, service: WebhookServiceDep
) -> WebhookSubscriptionRead:
    return await service.create(payload)


@router.get(
    "",
    response_model=list[WebhookSubscriptionRead],
    summary="List webhook subscriptions",
)
async def list_webhooks(service: WebhookServiceDep) -> list[WebhookSubscriptionRead]:
    return await service.list_all()


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove a webhook subscription",
)
async def delete_webhook(webhook_id: uuid.UUID, service: WebhookServiceDep) -> None:
    await service.delete(webhook_id)
