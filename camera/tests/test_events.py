from __future__ import annotations

from app.core.dependencies import get_camera_command_dispatcher
from app.main import app


class RecordingDispatcher:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def dispatch(self, command: str, params: dict) -> bool:
        self.calls.append((command, params))
        return True


async def test_trigger_event_dispatches_mapped_command(client):
    dispatcher = RecordingDispatcher()
    app.dependency_overrides[get_camera_command_dispatcher] = lambda: dispatcher

    try:
        response = await client.post(
            "/events/trigger",
            json={
                "event_type": "cat_detected",
                "camera_id": "front-yard",
                "metadata": {"confidence": 0.9},
            },
        )
        assert response.status_code == 202
        body = response.json()
        assert body["accepted"] is True
        assert body["command_dispatched"] == "light_on"
        assert body["command_success"] is True
        assert dispatcher.calls == [("light_on", {"duration_seconds": 30})]
    finally:
        del app.dependency_overrides[get_camera_command_dispatcher]


async def test_trigger_event_without_mapping_does_not_dispatch(client):
    dispatcher = RecordingDispatcher()
    app.dependency_overrides[get_camera_command_dispatcher] = lambda: dispatcher

    try:
        response = await client.post(
            "/events/trigger",
            json={"event_type": "unmapped_event", "camera_id": "front-yard", "metadata": {}},
        )
        assert response.status_code == 202
        body = response.json()
        assert body["command_dispatched"] is None
        assert dispatcher.calls == []
    finally:
        del app.dependency_overrides[get_camera_command_dispatcher]


async def test_events_log_shows_recent_events(client):
    await client.post(
        "/events/trigger",
        json={"event_type": "cat_detected", "camera_id": "front-yard", "metadata": {}},
    )
    response = await client.get("/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "cat_detected"


async def test_command_mapping_crud(client):
    get_resp = await client.get("/events/commands/cat_detected")
    assert get_resp.status_code == 200
    assert get_resp.json()["command"] == "light_on"

    put_resp = await client.put(
        "/events/commands/cat_detected", json={"command": "siren_on", "params": {"x": 1}}
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["command"] == "siren_on"

    delete_resp = await client.delete("/events/commands/cat_detected")
    assert delete_resp.status_code == 204

    missing_resp = await client.get("/events/commands/cat_detected")
    assert missing_resp.status_code == 404


async def test_events_trigger_requires_api_key_when_configured(client, monkeypatch):
    from app.settings.config import settings

    monkeypatch.setattr(settings, "events_api_key", "secret-key")
    try:
        unauthorized = await client.post(
            "/events/trigger",
            json={"event_type": "cat_detected", "camera_id": "front-yard", "metadata": {}},
        )
        assert unauthorized.status_code == 401

        authorized = await client.post(
            "/events/trigger",
            json={"event_type": "cat_detected", "camera_id": "front-yard", "metadata": {}},
            headers={"X-API-Key": "secret-key"},
        )
        assert authorized.status_code == 202
    finally:
        monkeypatch.setattr(settings, "events_api_key", None)
