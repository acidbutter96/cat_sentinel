"""Cross-domain DI providers: httpx clients for the upstream services.

hub has no database of its own, so instead of a DB session dependency this
module's cross-cutting concern is "how do we reach cat-sentinel / camera."

Two DISTINCT httpx.AsyncClient instances are kept for cat-sentinel, on
purpose -- this is a deliberate past design decision, not an oversight:

  * get_cat_sentinel_control_client -- a normal client WITH a sane timeout
    (settings.upstream_control_timeout). Used for control-plane calls like
    GET /cats/ and GET /detections/ that back /trackers. These should fail
    fast if cat-sentinel is slow or down, so hub can turn that into a clean
    502 rather than hanging the request.

  * get_cat_sentinel_stream_client -- a SEPARATE client with timeout=None.
    Used only for proxying GET /stream/annotated. An MJPEG multipart stream
    is long-lived by design (the connection is meant to stay open
    indefinitely while frames trickle in) -- applying the control-plane
    timeout to it would cut the stream off mid-proxy. Do NOT reuse the
    control client for streaming, and do NOT give this client a timeout
    "to be safe" -- that reintroduces the original bug this split fixes.

Both clients are created once at startup (see app/main.py lifespan) and
attached to app.state so they're reused across requests instead of paying
new-connection-pool setup cost per request, and so they can be closed
cleanly on shutdown.
"""

from collections.abc import AsyncGenerator

import httpx
from fastapi import Request

from app.settings.config import settings


def build_cat_sentinel_control_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.cat_sentinel_base_url,
        timeout=settings.upstream_control_timeout,
    )


def build_cat_sentinel_stream_client() -> httpx.AsyncClient:
    # timeout=None: never cut off a long-lived MJPEG stream. See module
    # docstring above for why this must stay a separate client.
    return httpx.AsyncClient(
        base_url=settings.cat_sentinel_base_url,
        timeout=None,
    )


async def get_cat_sentinel_control_client(
    request: Request,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    yield request.app.state.cat_sentinel_control_client


async def get_cat_sentinel_stream_client(
    request: Request,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    yield request.app.state.cat_sentinel_stream_client
