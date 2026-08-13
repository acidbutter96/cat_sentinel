"""Generic JSON passthrough to cat-sentinel, shared by every domain router
(cats/zones/alerts/activities) that's a straight 1:1 proxy rather than an
aggregation like app.trackers.

The browser never talks to cat-sentinel directly (see app/core/dependencies.py
module docstring on why hub exists at all) -- these routers exist purely so
hub_frontend has a same-origin path to reach cat-sentinel's CRUD endpoints.
Response bodies are passed through as-is (dict/list[dict]) rather than
re-declared as duplicate pydantic schemas here: cat-sentinel already owns
and validates that shape, and hub_frontend already treats this data as
loosely-typed on the way in (see hub_frontend/lib/types.ts's "permissive"
typing convention) -- round-tripping it through a second, hand-maintained
schema would just be a second place for the two services' contracts to
drift apart, exactly like the historical trackers bug this module's sibling
(app.trackers.service) had to fix.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.decorators import log_call
from app.core.exceptions import UpstreamServiceError


class UpstreamProxyService:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    @log_call
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = await self._client.request(method, path, params=params, json=json_body)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise UpstreamServiceError(f"cat-sentinel unreachable: {exc}") from exc

        if response.is_error:
            detail = response.text
            raise UpstreamServiceError(
                f"cat-sentinel returned {response.status_code} for {method} {path}: {detail}"
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()
