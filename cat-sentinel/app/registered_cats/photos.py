from __future__ import annotations

import uuid
from pathlib import Path

import cv2
import numpy as np

from app.settings.config import settings

MAX_PHOTO_BYTES = 5 * 1024 * 1024
_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_photo(
    cat_id: uuid.UUID,
    content_type: str,
    image_bytes: bytes,
) -> tuple[str, list[float] | None]:
    """Validate and persist a registered cat profile image.

    Files are stored outside the database. The returned relative path is the
    only value persisted on ``registered_cats``.
    """
    extension = _IMAGE_EXTENSIONS.get(content_type.lower())
    if extension is None:
        raise ValueError("Only JPEG, PNG, and WebP images are accepted")
    if not image_bytes or len(image_bytes) > MAX_PHOTO_BYTES:
        raise ValueError("Image must be between 1 byte and 5 MB")
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image data")

    root = Path(settings.registered_cat_image_dir)
    relative_path = root / str(cat_id) / f"profile_{uuid.uuid4().hex}{extension}"
    absolute_path = Path.cwd() / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = absolute_path.with_suffix(f"{extension}.tmp")
    temporary_path.write_bytes(image_bytes)
    temporary_path.replace(absolute_path)
    from app.vision.reid import compute_embedding

    height, width = image.shape[:2]
    embedding = compute_embedding(image, (0, 0, width, height))
    return relative_path.as_posix(), embedding


def resolve_photo(photo_path: str) -> Path:
    root = (Path.cwd() / settings.registered_cat_image_dir).resolve()
    resolved = (Path.cwd() / photo_path).resolve()
    if root not in resolved.parents or not resolved.is_file():
        raise FileNotFoundError(photo_path)
    return resolved
