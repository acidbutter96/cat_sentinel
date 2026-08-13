"""Proxies cat-sentinel's /activities/ so hub_frontend's activity timeline
page can read cat activity without talking to cat-sentinel directly. See
app/proxy/service.py.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_cat_sentinel_control_client
from app.proxy.service import UpstreamProxyService

router = APIRouter(prefix="/activities", tags=["activities"])


def get_proxy(
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> UpstreamProxyService:
    return UpstreamProxyService(control_client)


ProxyDep = Annotated[UpstreamProxyService, Depends(get_proxy)]


@router.get("", summary="List activity timeline entries")
async def list_activities(
    proxy: ProxyDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, Any]]:
    return await proxy.request("GET", "/activities/", params={"limit": limit, "offset": offset})
