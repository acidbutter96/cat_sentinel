"""Proxies cat-sentinel's /zones/ so hub_frontend's danger-zone editor can
list, create, update, and delete zones without talking to cat-sentinel
directly. See app/proxy/service.py.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Body, Depends, status

from app.core.dependencies import get_cat_sentinel_control_client
from app.proxy.service import UpstreamProxyService

router = APIRouter(prefix="/zones", tags=["zones"])


def get_proxy(
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> UpstreamProxyService:
    return UpstreamProxyService(control_client)


ProxyDep = Annotated[UpstreamProxyService, Depends(get_proxy)]


@router.get("", summary="List zones")
async def list_zones(proxy: ProxyDep) -> list[dict[str, Any]]:
    return await proxy.request("GET", "/zones/")


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a zone")
async def create_zone(
    proxy: ProxyDep, payload: Annotated[dict[str, Any], Body()]
) -> dict[str, Any]:
    return await proxy.request("POST", "/zones/", json_body=payload)


@router.get("/{zone_id}", summary="Get a zone")
async def get_zone(zone_id: str, proxy: ProxyDep) -> dict[str, Any]:
    return await proxy.request("GET", f"/zones/{zone_id}")


@router.patch("/{zone_id}", summary="Update a zone")
async def update_zone(
    zone_id: str, proxy: ProxyDep, payload: Annotated[dict[str, Any], Body()]
) -> dict[str, Any]:
    return await proxy.request("PATCH", f"/zones/{zone_id}", json_body=payload)


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a zone",
)
async def delete_zone(zone_id: str, proxy: ProxyDep) -> None:
    await proxy.request("DELETE", f"/zones/{zone_id}")
