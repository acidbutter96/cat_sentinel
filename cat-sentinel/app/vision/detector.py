from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from app.settings.config import settings

logger = logging.getLogger(__name__)

# COCO class index for "cat" (the pretrained YOLOv8 COCO weights class list).
COCO_CAT_CLASS_ID = 15
COCO_CAT_CLASS_NAME = "cat"


@dataclass(frozen=True)
class RawDetection:
    """A single YOLO detection for one frame, already filtered to cats."""

    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class YoloCatDetector:
    """Runs YOLOv8 (ultralytics) on a frame and returns only "cat" detections
    above the configured confidence threshold.

    The ultralytics model is loaded lazily on first use so importing this
    module (e.g. for unit tests of other vision components) doesn't require
    downloading/loading model weights.
    """

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float | None = None,
    ):
        self.model_path = model_path or settings.yolo_model_path
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.yolo_confidence_threshold
        )
        self._model = None

    def _get_model(self):
        if self._model is None:
            from ultralytics import YOLO

            logger.info("loading YOLO model from %s", self.model_path)
            self._model = YOLO(self.model_path)
        return self._model

    def detect(self, frame: np.ndarray) -> list[RawDetection]:
        """Runs inference on a single BGR frame (as decoded by OpenCV) and
        returns cat-only detections above the confidence threshold.
        """
        model = self._get_model()
        results = model.predict(
            source=frame,
            classes=[COCO_CAT_CLASS_ID],
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections: list[RawDetection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(
                    RawDetection(bbox=(xyxy[0], xyxy[1], xyxy[2], xyxy[3]), confidence=conf)
                )
        return detections
