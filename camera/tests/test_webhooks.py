from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.events.schemas import EventTrigger
from app.webhooks.service import WebhookService


async def test_webhook_crud(client):
    create = await client.post("/webhooks", json={"url": "https://example.com/hook"})
    assert create.status_code == 201
    webhook_id = create.json()["id"]

    listing = await client.get("/webhooks")
    assert listing.status_code == 200
    assert any(w["id"] == webhook_id for w in listing.json())

    delete = await client.delete(f"/webhooks/{webhook_id}")
    assert delete.status_code == 204

    missing_delete = await client.delete(f"/webhooks/{webhook_id}")
    assert missing_delete.status_code == 404


async def test_webhook_fanout_calls_matching_subscribers(monkeypatch):
    service = WebhookService()
    from app.webhooks.schemas import WebhookSubscriptionCreate

    await service.create(WebhookSubscriptionCreate(url="https://a.example/hook", event_types=None))
    await service.create(
        WebhookSubscriptionCreate(url="https://b.example/hook", event_types=["other_event"])
    )

    calls: list[str] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            calls.append(url)
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    trigger = EventTrigger(
        event_type="cat_detected",
        camera_id="front-yard",
        metadata={},
        timestamp=datetime.now(UTC),
    )
    notified = await service.notify_all(trigger)

    assert notified == 1
    assert calls == ["https://a.example/hook"]


async def test_webhook_fanout_swallows_failures(monkeypatch):
    from app.webhooks.schemas import WebhookSubscriptionCreate

    service = WebhookService()
    await service.create(
        WebhookSubscriptionCreate(url="https://broken.example/hook", event_types=None)
    )

    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            raise httpx.ConnectTimeout("boom")

    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)

    trigger = EventTrigger(
        event_type="cat_detected", camera_id="front-yard", metadata={}, timestamp=datetime.now(UTC)
    )
    # must not raise
    notified = await service.notify_all(trigger)
    assert notified == 0
