from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.dependencies import get_cat_sentinel_control_client
from app.main import app
from app.trackers.service import bounding_box_from_bbox, parse_captured_at

# Shape matches cat-sentinel's real GET /detected-cats/ and GET /detections/
# actually return (app.cats.schemas.CatRead / app.detections.schemas.DetectionRead)
# -- label/bbox/timestamp, NOT name/bounding_box/captured_at. Mocking the
# wrong shape here is exactly how the historical field-mismatch bug (see
# app/trackers/service.py's module docstring) went unnoticed.
CATS = [
    {"id": "cat-1", "label": "Whiskers"},
    {"id": "cat-2", "label": "Mittens"},
]


def _detections(now: datetime) -> list[dict]:
    older = (now - timedelta(minutes=5)).isoformat()
    newer = (now - timedelta(seconds=1)).isoformat()
    return [
        {
            "id": "det-1",
            "cat_id": "cat-1",
            "bbox": [1.0, 2.0, 11.0, 22.0],
            "timestamp": older,
            "in_danger_zone": False,
            "snapshot_path": "snapshots/default/cat-1/old.jpg",
            "frame_path": "snapshots/default/cat-1/old_frame.jpg",
            "track_id": 31,
        },
        {
            "id": "det-2",
            "cat_id": "cat-1",
            "bbox": [5.0, 6.0, 15.0, 26.0],
            "timestamp": newer,
            "in_danger_zone": True,
            "confidence": 0.91,
            "track_id": 31,
        },
        {
            "id": "det-3",
            "cat_id": "cat-2",
            "bbox": [0.0, 0.0, 5.0, 5.0],
            "timestamp": newer,
            "in_danger_zone": False,
        },
    ]


def _handler_factory(now: datetime):
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/detected-cats/":
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
    assert cat_1["in_danger_zone"] is True
    assert cat_1["snapshot_path"] == "snapshots/default/cat-1/old.jpg"
    assert cat_1["entry_frame_path"] == "snapshots/default/cat-1/old_frame.jpg"
    assert cat_1["entry_track_id"] == 31
    assert cat_1["entry_bounding_box"] == {"x": 1.0, "y": 2.0, "width": 10.0, "height": 20.0}
    assert cat_1["confidence"] == 0.91

    cat_2 = next(t for t in body if t["cat_id"] == "cat-2")
    assert cat_2["cat_name"] == "Mittens"
    assert cat_2["in_danger_zone"] is False


async def test_list_trackers_excludes_stale_detections(client, mock_control_client):
    response = await client.get("/trackers")
    assert all(tracker["age_seconds"] <= 8.0 for tracker in response.json())


def test_bounding_box_from_bbox_converts_corner_pair_to_xywh():
    box = bounding_box_from_bbox([5.0, 6.0, 15.0, 26.0])
    assert box.x == 5.0
    assert box.y == 6.0
    assert box.width == 10.0
    assert box.height == 20.0


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
