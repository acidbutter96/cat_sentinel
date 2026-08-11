from __future__ import annotations

import asyncio
import contextlib


class AnnotatedFrameBroadcaster:
    """In-memory pub/sub of the latest annotated JPEG frame.

    The detection pipeline is the sole publisher (via `publish`); any number
    of HTTP clients can `subscribe` without causing extra detector work --
    subscribing just registers a queue that receives a copy of each newly
    published frame.

    Must be created at app-construction time (see app.main), not inside
    FastAPI's lifespan, so `app.state.broadcaster` always exists before any
    request can be routed -- routes must never see a missing broadcaster
    even if the pipeline hasn't started publishing yet.
    """

    def __init__(self, max_queue_size: int = 2):
        self._max_queue_size = max_queue_size
        self._subscribers: set[asyncio.Queue[bytes]] = set()
        self._latest_frame: bytes | None = None
        self._lock = asyncio.Lock()

    async def publish(self, jpeg_bytes: bytes) -> None:
        self._latest_frame = jpeg_bytes
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            if queue.full():
                # Drop the oldest buffered frame rather than blocking the
                # publisher on a slow subscriber.
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(jpeg_bytes)

    async def subscribe(self) -> asyncio.Queue[bytes]:
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self._max_queue_size)
        if self._latest_frame is not None:
            queue.put_nowait(self._latest_frame)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[bytes]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    @property
    def latest_frame(self) -> bytes | None:
        return self._latest_frame
