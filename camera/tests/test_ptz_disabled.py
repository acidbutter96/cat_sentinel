from __future__ import annotations

import pytest

from app.core.dependencies import get_ptz_controller
from app.core.exceptions import PTZDisabledError


async def test_health_reports_ptz_enabled_flag(client, monkeypatch):
    from app.settings.config import settings

    monkeypatch.setattr(settings, "ptz_enabled", True)
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ptz_enabled": True}

    monkeypatch.setattr(settings, "ptz_enabled", False)
    response = await client.get("/health")
    assert response.json() == {"status": "ok", "ptz_enabled": False}


class _FakeAppState:
    def __init__(self, ptz_controller):
        self.ptz_controller = ptz_controller


class _FakeApp:
    def __init__(self, ptz_controller):
        self.state = _FakeAppState(ptz_controller)


class _FakeRequest:
    def __init__(self, ptz_controller):
        self.app = _FakeApp(ptz_controller)


def test_get_ptz_controller_raises_when_disabled():
    request = _FakeRequest(ptz_controller=None)
    with pytest.raises(PTZDisabledError):
        get_ptz_controller(request)


def test_get_ptz_controller_returns_instance_when_enabled():
    sentinel = object()
    request = _FakeRequest(ptz_controller=sentinel)
    assert get_ptz_controller(request) is sentinel


async def test_ptz_routes_503_when_ptz_disabled(client):
    from app.main import app

    def _raise_disabled():
        raise PTZDisabledError

    app.dependency_overrides[get_ptz_controller] = _raise_disabled
    try:
        response = await client.get("/ptz/status")
        assert response.status_code == 503
        assert response.json() == {"detail": "PTZ control is disabled (PTZ_ENABLED=false)"}
    finally:
        del app.dependency_overrides[get_ptz_controller]
