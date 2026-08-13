from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np


def _safe_path_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "default"


def save_cat_snapshot(
    frame: np.ndarray,
    bbox: tuple[float, float, float, float],
    *,
    output_dir: str,
    camera_id: str,
    cat_id: uuid.UUID,
    captured_at: datetime | None = None,
) -> str | None:
    """Save a padded crop of a detected cat and return its relative path.

    The returned path is relative to the application working directory so it
    remains portable between local runs and the Docker bind mount.
    """
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    box_width = max(x2 - x1, 1.0)
    box_height = max(y2 - y1, 1.0)
    padding_x = box_width * 0.1
    padding_y = box_height * 0.1
    left = max(0, int(x1 - padding_x))
    top = max(0, int(y1 - padding_y))
    right = min(width, int(x2 + padding_x))
    bottom = min(height, int(y2 + padding_y))
    if right <= left or bottom <= top:
        return None

    captured_at = captured_at or datetime.now(UTC)
    timestamp = captured_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    camera_part = _safe_path_part(camera_id)
    filename = f"{timestamp}_{uuid.uuid4().hex}.jpg"
    relative_path = Path(output_dir) / camera_part / str(cat_id) / filename
    absolute_path = Path(relative_path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(absolute_path), frame[top:bottom, left:right]):
        raise OSError(f"failed to write cat snapshot to {absolute_path}")
    return relative_path.as_posix()


def save_entry_frame(
    frame: np.ndarray,
    *,
    output_dir: str,
    camera_id: str,
    cat_id: uuid.UUID,
    captured_at: datetime,
) -> str:
    """Save the complete camera frame for a new-track selection event."""
    timestamp = captured_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    camera_part = _safe_path_part(camera_id)
    filename = f"{timestamp}_{uuid.uuid4().hex}_frame.jpg"
    relative_path = Path(output_dir) / camera_part / str(cat_id) / filename
    absolute_path = Path(relative_path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(absolute_path), frame):
        raise OSError(f"failed to write entry frame to {absolute_path}")
    return relative_path.as_posix()
