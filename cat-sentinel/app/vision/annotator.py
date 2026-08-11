from __future__ import annotations

import cv2
import numpy as np

DEFAULT_BOX_COLOR = (0, 200, 0)  # BGR green
DANGER_BOX_COLOR = (0, 0, 255)  # BGR red
TEXT_COLOR = (255, 255, 255)  # BGR white


class FrameAnnotator:
    """Draws bounding boxes and a cat name/track-id label onto a frame.
    Red box when the cat is inside a danger zone, default color otherwise.
    """

    def annotate(
        self,
        frame: np.ndarray,
        boxes: list[tuple[tuple[float, float, float, float], str, bool]],
    ) -> np.ndarray:
        """`boxes` is a list of (bbox, label, in_danger_zone) tuples.
        Returns a new frame with boxes and labels burned in (does not
        mutate the input array in place beyond what cv2.rectangle/putText do
        on the copy returned here).
        """
        annotated = frame.copy()
        for (x1, y1, x2, y2), label, in_danger_zone in boxes:
            color = DANGER_BOX_COLOR if in_danger_zone else DEFAULT_BOX_COLOR
            pt1 = (int(x1), int(y1))
            pt2 = (int(x2), int(y2))
            cv2.rectangle(annotated, pt1, pt2, color, 2)

            text_origin = (int(x1), max(int(y1) - 8, 0))
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                annotated,
                (text_origin[0], text_origin[1] - text_h - 4),
                (text_origin[0] + text_w + 4, text_origin[1] + 2),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (text_origin[0] + 2, text_origin[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                TEXT_COLOR,
                1,
                cv2.LINE_AA,
            )
        return annotated

    def encode_jpeg(self, frame: np.ndarray) -> bytes:
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            raise ValueError("failed to encode frame as JPEG")
        return buffer.tobytes()
