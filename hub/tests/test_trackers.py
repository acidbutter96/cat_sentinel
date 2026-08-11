from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.dependencies import get_cat_sentinel_control_client
from app.main import app
from app.trackers.service import parse_captured_at

CATS = [
    {"id": "cat-1", "name": "Whiskers"},
    {"id": "cat-2", "name": "Mittens"},
]


def _detections(now: datetime) -> list[dict]:
    older = (now - timedelta(minutes=5)).isoformat()
    newer = (now - timedelta(seconds=10)).isoformat()
    return [
        {
            "id": "det-1",
            "cat_id": "cat-1",
            "bounding_box": {"x": 1.0, "y": 2.0, "width": 10.0, "height": 20.0},
            "captured_at": older,
        },
        {
            "id": "det-2",
            "cat_id": "cat-1",
            "bounding_box": {"x": 5.0, "y": 6.0, "width": 10.0, "height": 20.0},
            "captured_at": newer,
        },
        {
            "id": "det-3",
            "cat_id": "cat-2",
            "bounding_box": {"x": 0.0, "y": 0.0, "width": 5.0, "height": 5.0},
            "captured_at": newer,
        },
    ]


def _handler_factory(now: datetime):
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cats/":
            return httpx.Response(200, json=CATS)
        if request.url.path == "/detections/":
            return httpx.Response(200, json=_detections(now))
        return httpx.Response(404)
    return handler


@pytest.fixture
async def mock_control_client():
    now = datetime.now(UTC)
    transport = httpx.MockTransport(_handler_factory(now))
    client = httpx.AsyncClient(transport=transport, base_url="http://cat-sentinel.test")

    async def _override():
        yield client

    app.dependency_overrides[get_cat_sentinel_control_client] = _override
    yield client
    app.dependency_overrides.clear()
    await client.aclose()


async def test_list_trackers_returns_latest_bbox_per_cat(client, mock_control_client):
    response = await client.get("/trackers")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2

    cat_1 = next(t for t in body if t["cat_id"] == "cat-1")
    assert cat_1["cat_name"] == "Whiskers"
    # the newer detection's bbox should win
    assert cat_1["bounding_box"] == {"x": 5.0, "y": 6.0, "width": 10.0, "height": 20.0}

    cat_2 = next(t for t in body if t["cat_id"] == "cat-2")
    assert cat_2["cat_name"] == "Mittens"


@pytest.fixture
async def unreachable_control_client():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://cat-sentinel.test")

    async def _override():
        yield client

    app.dependency_overrides[get_cat_sentinel_control_client] = _override
    yield client
    app.dependency_overrides.clear()
    await client.aclose()


async def test_list_trackers_upstream_down_returns_502(client, unreachable_control_client):
    response = await client.get("/trackers")
    assert response.status_code == 502


# --- Regression test for the historical tz-naive bug ---------------------


def test_parse_captured_at_normalizes_naive_datetime_to_utc():
    """Historical bug: captured_at from upstream JSON could be tz-naive
    (e.g. "2026-08-09T12:00:00" with no offset), and subtracting it from a
    tz-aware `datetime.now(timezone.utc)` raised:

        TypeError: can't subtract offset-naive and offset-aware datetimes

    parse_captured_at must normalize naive input to UTC-aware so this never
    happens again.
    """
    naive_str = "2026-08-09T12:00:00"
    parsed = parse_captured_at(naive_str)

    assert parsed.tzinfo is not None

    now = datetime(2026, 8, 9, 12, 0, 30, tzinfo=UTC)
    # must not raise TypeError
    age = (now - parsed).total_seconds()
    assert age == pytest.approx(30.0)


def test_parse_captured_at_preserves_aware_datetime():
    aware_str = "2026-08-09T12:00:00+00:00"
    parsed = parse_captured_at(aware_str)
    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)
