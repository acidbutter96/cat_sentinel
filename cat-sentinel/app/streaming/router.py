from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.exceptions import FrameNotAvailableError
from app.streaming.broadcaster import AnnotatedFrameBroadcaster

router = APIRouter(prefix="/stream", tags=["streaming"])

_BOUNDARY = "frame"


async def _mjpeg_generator(broadcaster: AnnotatedFrameBroadcaster) -> AsyncIterator[bytes]:
    queue = await broadcaster.subscribe()
    try:
        while True:
            frame = await queue.get()
            yield (
                b"--" + _BOUNDARY.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
            )
    except asyncio.CancelledError:
        raise
    finally:
        await broadcaster.unsubscribe(queue)


@router.get("/annotated", summary="MJPEG stream of annotated frames with bounding boxes burned in")
async def stream_annotated(request: Request) -> StreamingResponse:
    broadcaster: AnnotatedFrameBroadcaster = request.app.state.broadcaster
    if broadcaster.latest_frame is None:
        raise FrameNotAvailableError(
            "No annotated frame available yet -- pipeline may still be starting"
        )
    return StreamingResponse(
        _mjpeg_generator(broadcaster),
        media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}",
    )
