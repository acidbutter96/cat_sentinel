from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.dependencies import get_cat_sentinel_control_client
from app.core.exceptions import UpstreamServiceError

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.get("", summary="Proxy a stored cat snapshot")
async def get_snapshot(
    path: Annotated[str, Query(min_length=1)],
    client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> Response:
    try:
        upstream = await client.get("/snapshots", params={"path": path})
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise UpstreamServiceError(f"cat-sentinel unreachable: {exc}") from exc

    if upstream.status_code == 404:
        return Response(status_code=404)
    if upstream.is_error:
        raise UpstreamServiceError(
            f"cat-sentinel returned {upstream.status_code} for snapshot"
        )

    return Response(
        content=upstream.content,
        media_type=upstream.headers.get("content-type", "image/jpeg"),
        headers={"cache-control": "public, max-age=60"},
    )
