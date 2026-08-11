from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

_BOUNDARY_MARKER = b"--"
_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI = b"\xff\xd9"


class RatSentinelStreamClient:
    """httpx-based MJPEG multipart frame puller.

    Connects to the upstream camera service's `multipart/x-mixed-replace`
    MJPEG stream and yields raw JPEG frame bytes as they arrive. Named after
    the upstream camera service (rat-sentinel) this client talks to.
    """

    def __init__(self, stream_url: str, timeout: float = 10.0):
        self.stream_url = stream_url
        self.timeout = timeout

    async def frames(self) -> AsyncIterator[bytes]:
        """Yields raw JPEG bytes for each frame in the MJPEG stream.

        Parses the multipart stream by buffering bytes and slicing out each
        JPEG payload between its SOI (0xFFD8) and EOI (0xFFD9) markers --
        robust to arbitrary chunk boundaries and to boundary/header lines
        interleaved between frames, without needing a full multipart parser.
        """
        buffer = b""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("GET", self.stream_url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    buffer += chunk
                    while True:
                        start = buffer.find(_JPEG_SOI)
                        if start == -1:
                            # No frame start yet; keep only a small tail in
                            # case a marker is split across chunks.
                            if len(buffer) > 2:
                                buffer = buffer[-2:]
                            break
                        end = buffer.find(_JPEG_EOI, start + 2)
                        if end == -1:
                            # Frame start found but not finished yet.
                            buffer = buffer[start:]
                            break
                        frame = buffer[start : end + 2]
                        buffer = buffer[end + 2 :]
                        yield frame
