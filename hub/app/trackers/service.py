"""Business logic for aggregating upstream cat-sentinel data into trackers.

Historical bug (fixed here, with a regression test in tests/test_trackers.py):
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
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.decorators import log_errors
from app.core.exceptions import UpstreamServiceError
from app.trackers.schemas import BoundingBox, TrackerRead


def parse_captured_at(raw: str) -> datetime:
    """Parse an upstream `captured_at` timestamp string into a UTC-aware
    datetime, normalizing tz-naive input.

    This is the regression-tested fix for the historical tz-naive bug
    described in this module's docstring. Isolated as a standalone function
    (rather than inlined in list_active_trackers) so it can be unit tested
    directly with no HTTP or mocking involved.
    """
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


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
        for detection in detections:
            cat_id = detection["cat_id"]
            captured_at = parse_captured_at(detection["captured_at"])
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
            bbox = detection["bounding_box"]
            trackers.append(
                TrackerRead(
                    cat_id=cat_id,
                    cat_name=cats_by_id.get(cat_id, {}).get("name"),
                    bounding_box=BoundingBox(**bbox),
                    captured_at=captured_at,
                    age_seconds=age_seconds,
                )
            )
        trackers.sort(key=lambda t: t.cat_id)
        return trackers

    async def _fetch_cats(self) -> dict[str, dict[str, Any]]:
        response = await self._get("/cats/")
        return {cat["id"]: cat for cat in response.json()}

    async def _fetch_detections(self) -> list[dict[str, Any]]:
        response = await self._get("/detections/")
        result: list[dict[str, Any]] = response.json()
        return result

    async def _get(self, path: str) -> httpx.Response:
        try:
            response = await self._client.get(path)
            response.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise UpstreamServiceError(f"cat-sentinel unreachable: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise UpstreamServiceError(
                f"cat-sentinel returned {exc.response.status_code} for {path}"
            ) from exc
        return response
