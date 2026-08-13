"""Covers the thin cats/zones/alerts/activities proxy routers -- each just
forwards to cat-sentinel and passes the JSON body through unchanged (see
app/proxy/service.py), so one list + one write test per domain is enough to
catch a wrong upstream path/method rather than re-testing cat-sentinel's own
business logic here.
"""

import httpx
import pytest

from app.core.dependencies import get_cat_sentinel_control_client
from app.main import app

from .conftest import MockTransport


@pytest.fixture
async def upstream(request):
    """Builds a mock cat-sentinel client from the `handler` the test passes
    in via indirect parametrization, and overrides hub's control-client
    dependency with it for the duration of the test.
    """
    handler = request.param
    client = httpx.AsyncClient(
        transport=MockTransport(handler), base_url="http://cat-sentinel.test"
    )

    async def _override():
        yield client

    app.dependency_overrides[get_cat_sentinel_control_client] = _override
    yield client
    app.dependency_overrides.clear()
    await client.aclose()


async def _cats_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/cats/" and request.method == "GET":
        return httpx.Response(200, json=[{"id": "cat-1", "name": "Whiskers"}])
    if request.url.path == "/cats/" and request.method == "POST":
        assert request.content
        return httpx.Response(201, json={"id": "cat-2", "name": "Mittens"})
    if request.url.path == "/cats/cat-1" and request.method == "PATCH":
        assert request.content
        return httpx.Response(200, json={"id": "cat-1", "name": "Renamed"})
    return httpx.Response(404)


@pytest.mark.parametrize("upstream", [_cats_handler], indirect=True)
async def test_list_register_and_update_cat(client, upstream):
    listed = await client.get("/cats")
    assert listed.status_code == 200
    assert listed.json() == [{"id": "cat-1", "name": "Whiskers"}]

    registered = await client.post("/cats", json={"name": "Mittens"})
    assert registered.status_code == 201
    assert registered.json()["name"] == "Mittens"

    renamed = await client.patch("/cats/cat-1", json={"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"


async def _zones_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/zones/" and request.method == "GET":
        return httpx.Response(200, json=[])
    if request.url.path == "/zones/" and request.method == "POST":
        return httpx.Response(201, json={"id": "zone-1", "name": "kitchen"})
    if request.url.path == "/zones/zone-1" and request.method == "DELETE":
        return httpx.Response(204)
    return httpx.Response(404)


@pytest.mark.parametrize("upstream", [_zones_handler], indirect=True)
async def test_list_create_and_delete_zone(client, upstream):
    listed = await client.get("/zones")
    assert listed.status_code == 200
    assert listed.json() == []

    created = await client.post(
        "/zones",
        json={
            "camera_id": "default",
            "name": "kitchen",
            "points": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}],
        },
    )
    assert created.status_code == 201
    assert created.json()["name"] == "kitchen"

    deleted = await client.delete("/zones/zone-1")
    assert deleted.status_code == 204


async def _alerts_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/alerts/" and request.method == "GET":
        return httpx.Response(200, json=[{"id": "alert-1", "kind": "camera_entry"}])
    return httpx.Response(404)


@pytest.mark.parametrize("upstream", [_alerts_handler], indirect=True)
async def test_list_alerts(client, upstream):
    response = await client.get("/alerts")
    assert response.status_code == 200
    assert response.json() == [{"id": "alert-1", "kind": "camera_entry"}]


async def _activities_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/activities/" and request.method == "GET":
        return httpx.Response(200, json=[{"id": "act-1", "kind": "entered_frame"}])
    return httpx.Response(404)


@pytest.mark.parametrize("upstream", [_activities_handler], indirect=True)
async def test_list_activities(client, upstream):
    response = await client.get("/activities")
    assert response.status_code == 200
    assert response.json() == [{"id": "act-1", "kind": "entered_frame"}]
