"""Business logic for aggregating upstream cat-sentinel data into trackers.

Historical bug #1 (fixed here, with a regression test in tests/test_trackers.py):
TrackerService.list_active_trackers used to compute
`datetime.now(timezone.utc) - tracker.captured_at` directly against whatever
datetime came back from parsing the upstream JSON. `captured_at` as received
from upstream was sometimes timezone-naive (SQLite on the far side doesn't
reliably preserve tz info even when the column is declared
DateTime(timezone=True)), which raised:

    TypeError: can't subtract offset-naive and offset-aware datetimes

in production. The old test suite never caught this because its mocks always
generated tz-aware fake dates, so the naive case was never exercised.

Fix: `parse_captured_at` explicitly normalizes any naive datetime to
UTC-aware immediately after parsing, before it is ever compared/subtracted
against anything else. Every call site in this module goes through
`parse_captured_at` -- never `datetime.fromisoformat` directly -- so the
normalization can't be skipped.

Historical bug #2 (fixed here): this module was written against a
`captured_at`/`bounding_box {x,y,width,height}`/cat `name` shape that never
matched what cat-sentinel's `/cats/` and `/detections/` actually return
(`timestamp`, `bbox [x1, y1, x2, y2]`, cat `label`) -- every call to
GET /trackers KeyError'd. `_bounding_box_from_bbox` converts the corner-pair
`bbox` cat-sentinel really sends into the `{x, y, width, height}` shape
`TrackerRead`/the frontend expect.
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.decorators import log_errors
from app.core.exceptions import UpstreamServiceError
from app.settings.config import settings
from app.trackers.schemas import BoundingBox, TrackerRead


def parse_captured_at(raw: str) -> datetime:
    """Parse an upstream `timestamp` string into a UTC-aware datetime,
    normalizing tz-naive input.

    This is the regression-tested fix for the historical tz-naive bug
    described in this module's docstring. Isolated as a standalone function
    (rather than inlined in list_active_trackers) so it can be unit tested
    directly with no HTTP or mocking involved.
    """
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def bounding_box_from_bbox(bbox: list[float]) -> BoundingBox:
    """Converts cat-sentinel's `bbox` corner-pair shape ([x1, y1, x2, y2])
    into the {x, y, width, height} shape TrackerRead/the frontend expect.
    """
    x1, y1, x2, y2 = bbox
    return BoundingBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)


@log_errors
class TrackerService:
    def __init__(self, control_client: httpx.AsyncClient):
        self._client = control_client

    async def list_active_trackers(self) -> list[TrackerRead]:
        """Fetch the latest bounding box per tracked cat from upstream
        cat-sentinel's GET /cats/ + GET /detections/, and return one entry
        per actively-tracked cat with its most recent bounding box/position.

        Read-through, no caching for v1.
        """
        cats_by_id = await self._fetch_cats()
        detections = await self._fetch_detections()

        latest_by_cat: dict[str, dict[str, Any]] = {}
        latest_entry_by_cat: dict[str, dict[str, Any]] = {}
        latest_snapshot_by_cat: dict[str, str] = {}
        for detection in detections:
            cat_id = detection["cat_id"]
            captured_at = parse_captured_at(detection["timestamp"])
            if detection.get("snapshot_path") and cat_id not in latest_snapshot_by_cat:
                latest_snapshot_by_cat[cat_id] = detection["snapshot_path"]
            if detection.get("frame_path") and cat_id not in latest_entry_by_cat:
                latest_entry_by_cat[cat_id] = {**detection, "captured_at": captured_at}
            existing = latest_by_cat.get(cat_id)
            if existing is None or captured_at > existing["captured_at"]:
                latest_by_cat[cat_id] = {**detection, "captured_at": captured_at}

        now = datetime.now(UTC)
        trackers: list[TrackerRead] = []
        for cat_id, detection in latest_by_cat.items():
            captured_at = detection["captured_at"]
            # This subtraction is exactly the historical crash site -- both
            # operands MUST be tz-aware by the time we get here.
            age_seconds = (now - captured_at).total_seconds()
            if age_seconds > settings.tracker_stale_after_seconds:
                continue
            entry = latest_entry_by_cat.get(cat_id)
            trackers.append(
                TrackerRead(
                    cat_id=cat_id,
                    cat_name=cats_by_id.get(cat_id, {}).get("label"),
                    track_id=detection.get("track_id"),
                    bounding_box=bounding_box_from_bbox(detection["bbox"]),
                    captured_at=captured_at,
                    age_seconds=age_seconds,
                    in_danger_zone=bool(detection.get("in_danger_zone", False)),
                    confidence=detection.get("confidence"),
                    snapshot_path=detection.get("snapshot_path")
                    or latest_snapshot_by_cat.get(cat_id),
                    entry_frame_path=entry.get("frame_path") if entry else None,
                    entry_track_id=entry.get("track_id") if entry else None,
                    entry_bounding_box=(
                        bounding_box_from_bbox(entry["bbox"]) if entry else None
                    ),
                    entry_captured_at=entry.get("captured_at") if entry else None,
                )
            )
        trackers.sort(key=lambda t: t.cat_id)
        return trackers

    async def _fetch_cats(self) -> dict[str, dict[str, Any]]:
        response = await self._get("/detected-cats/", params={"limit": 200})
        return {cat["id"]: cat for cat in response.json()}

    async def _fetch_detections(self) -> list[dict[str, Any]]:
        response = await self._get("/detections/", params={"limit": 200})
        result: list[dict[str, Any]] = response.json()
        return result

    async def _get(
        self, path: str, params: dict[str, int] | None = None
    ) -> httpx.Response:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise UpstreamServiceError(f"cat-sentinel unreachable: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise UpstreamServiceError(
                f"cat-sentinel returned {exc.response.status_code} for {path}"
            ) from exc
        return response
