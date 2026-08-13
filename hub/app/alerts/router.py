"""Proxies cat-sentinel's /alerts/ so hub_frontend's alert history page can
read fired alerts without talking to cat-sentinel directly. See
app/proxy/service.py.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_cat_sentinel_control_client
from app.proxy.service import UpstreamProxyService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_proxy(
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> UpstreamProxyService:
    return UpstreamProxyService(control_client)


ProxyDep = Annotated[UpstreamProxyService, Depends(get_proxy)]


@router.get("", summary="List fired alerts")
async def list_alerts(
    proxy: ProxyDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, Any]]:
    return await proxy.request("GET", "/alerts/", params={"limit": limit, "offset": offset})
