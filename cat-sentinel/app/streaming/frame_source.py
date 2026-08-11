from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import cv2
import numpy as np

from app.streaming.client import RatSentinelStreamClient

logger = logging.getLogger(__name__)


class FrameSource:
    """Wraps RatSentinelStreamClient and decodes raw JPEG bytes into BGR
    numpy arrays (as OpenCV/YOLO expect), skipping frames that fail to
    decode instead of raising.
    """

    def __init__(self, client: RatSentinelStreamClient):
        self.client = client

    async def frames(self) -> AsyncIterator[np.ndarray]:
        async for raw_jpeg in self.client.frames():
            array = np.frombuffer(raw_jpeg, dtype=np.uint8)
            frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning("failed to decode a frame from the upstream MJPEG stream, skipping")
                continue
            yield frame
