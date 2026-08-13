"""Proxies the manual registered-cat profiles owned by cat-sentinel.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import Response

from app.core.dependencies import get_cat_sentinel_control_client
from app.core.exceptions import UpstreamServiceError
from app.proxy.service import UpstreamProxyService

router = APIRouter(prefix="/cats", tags=["cats"])


def get_proxy(
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> UpstreamProxyService:
    return UpstreamProxyService(control_client)


ProxyDep = Annotated[UpstreamProxyService, Depends(get_proxy)]


@router.get("", summary="List registered cats")
async def list_cats(proxy: ProxyDep) -> list[dict[str, Any]]:
    return await proxy.request("GET", "/cats/")


@router.post("", status_code=status.HTTP_201_CREATED, summary="Register a cat")
async def create_cat(
    proxy: ProxyDep, payload: Annotated[dict[str, Any], Body()]
) -> dict[str, Any]:
    return await proxy.request("POST", "/cats/", json_body=payload)


@router.get("/{cat_id}/photo", summary="Proxy a registered cat image")
async def get_cat_photo(
    cat_id: str,
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> Response:
    try:
        upstream = await control_client.get(f"/cats/{cat_id}/photo")
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise UpstreamServiceError(f"cat-sentinel unreachable: {exc}") from exc
    if upstream.status_code == 404:
        return Response(status_code=404)
    if upstream.is_error:
        raise UpstreamServiceError(f"cat-sentinel returned {upstream.status_code} for cat photo")
    return Response(
        content=upstream.content,
        media_type=upstream.headers.get("content-type", "image/jpeg"),
        headers={"cache-control": "public, max-age=60"},
    )


@router.post("/{cat_id}/images", summary="Upload a registered cat reference image")
async def upload_cat_image(
    cat_id: str,
    request: Request,
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> Response:
    try:
        upstream = await control_client.post(
            f"/cats/{cat_id}/images",
            content=await request.body(),
            headers={"content-type": request.headers.get("content-type", "")},
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise UpstreamServiceError(f"cat-sentinel unreachable: {exc}") from exc
    if upstream.is_error:
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "application/json"),
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


@router.get("/{cat_id}", summary="Get a cat")
async def get_cat(cat_id: str, proxy: ProxyDep) -> dict[str, Any]:
    return await proxy.request("GET", f"/cats/{cat_id}")


@router.patch("/{cat_id}", summary="Update a registered cat profile")
async def update_cat(
    cat_id: str, proxy: ProxyDep, payload: Annotated[dict[str, Any], Body()]
) -> dict[str, Any]:
    return await proxy.request("PATCH", f"/cats/{cat_id}", json_body=payload)
