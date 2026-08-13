from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_camera_stream_client
from app.stream.service import StreamService

router = APIRouter(tags=["stream"])


def get_stream_service(
    stream_client: Annotated[httpx.AsyncClient, Depends(get_camera_stream_client)],
) -> StreamService:
    return StreamService(stream_client)


StreamServiceDep = Annotated[StreamService, Depends(get_stream_service)]


@router.get(
    "/stream",
    summary="Proxy the camera MJPEG stream",
)
async def stream_camera(service: StreamServiceDep) -> StreamingResponse:
    upstream_response = await service.open_camera_stream()
    media_type = upstream_response.headers.get("content-type", "multipart/x-mixed-replace")
    return StreamingResponse(
        service.iter_camera_stream(upstream_response),
        media_type=media_type,
    )
