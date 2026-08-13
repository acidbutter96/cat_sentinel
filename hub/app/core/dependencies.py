"""HTTP clients for the detector metrics API and the camera video API.

The hub deliberately keeps a regular, bounded-timeout client for cat-sentinel
control-plane data and a separate timeout-free client for camera MJPEG. This
keeps the heavy video path out of the detector and avoids cutting off a live
stream with a control-plane timeout.
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


def build_camera_stream_client() -> httpx.AsyncClient:
    # timeout=None: an MJPEG connection is deliberately long-lived.
    return httpx.AsyncClient(
        base_url=settings.camera_base_url,
        timeout=None,
    )


async def get_cat_sentinel_control_client(
    request: Request,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    yield request.app.state.cat_sentinel_control_client


async def get_camera_stream_client(
    request: Request,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    yield request.app.state.camera_stream_client
