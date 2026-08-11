from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_cat_sentinel_stream_client
from app.stream.service import StreamService

router = APIRouter(tags=["stream"])


def get_stream_service(
    stream_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_stream_client)],
) -> StreamService:
    return StreamService(stream_client)


StreamServiceDep = Annotated[StreamService, Depends(get_stream_service)]


@router.get(
    "/stream/annotated",
    summary="Proxy the MJPEG annotated stream from upstream cat-sentinel",
)
async def stream_annotated(service: StreamServiceDep) -> StreamingResponse:
    upstream_response = await service.open_annotated_stream()
    media_type = upstream_response.headers.get("content-type", "multipart/x-mixed-replace")
    return StreamingResponse(
        service.iter_annotated_stream(upstream_response),
        media_type=media_type,
    )
