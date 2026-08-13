"""Proxies the camera MJPEG stream byte-for-byte.

Two things this module is careful about:

1. Connectivity is verified eagerly (via client.send(..., stream=True)) before
   any bytes are handed back to the router, so a downed/unreachable camera
   raises UpstreamServiceError -> 502 through the normal exception-handler
   path, instead of surfacing as a broken/empty StreamingResponse the client
   has already started reading.

2. The upstream httpx.Response is always closed in a `finally`, so when the
   downstream client disconnects mid-stream (closes the browser tab, etc.),
   Starlette throws GeneratorExit into iter_camera_stream and the `finally`
   still runs -- the upstream connection is never leaked.
"""

from collections.abc import AsyncGenerator

import httpx

from app.core.decorators import log_call
from app.core.exceptions import UpstreamServiceError

CAMERA_STREAM_PATH = "/video"


class StreamService:
    def __init__(self, stream_client: httpx.AsyncClient):
        self._client = stream_client

    # Not @log_errors: iter_camera_stream sits on a hot path (called
    # continuously while a stream is open) and would flood logs with a
    # debug/entry line per chunk if wrapped. open_camera_stream is
    # decorated individually instead since it only runs once per connection.
    @log_call
    async def open_camera_stream(self) -> httpx.Response:
        """Open the upstream MJPEG stream and verify connectivity.

        Returns the still-open httpx.Response (stream=True); the caller is
        responsible for eventually consuming it via iter_camera_stream,
        which guarantees it gets closed.
        """
        request = self._client.build_request("GET", CAMERA_STREAM_PATH)
        try:
            response = await self._client.send(request, stream=True)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise UpstreamServiceError(f"camera stream unreachable: {exc}") from exc

        if response.is_error:
            await response.aclose()
            raise UpstreamServiceError(
                f"camera returned {response.status_code} for {CAMERA_STREAM_PATH}"
            )
        return response

    async def iter_camera_stream(self, response: httpx.Response) -> AsyncGenerator[bytes, None]:
        """Yield upstream body chunks unchanged; always close upstream on exit,
        including when the downstream client disconnects early."""
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
