from __future__ import annotations

import cv2
import numpy as np

# HSV histogram bin counts (Hue, Saturation, Value). 8x8x8 = 512-dim vector.
EMBEDDING_BINS = (8, 8, 8)
MIN_CROP_DIMENSION = 8


def crop_bbox(frame: np.ndarray, bbox: tuple[float, float, float, float]) -> np.ndarray | None:
    """Crops `bbox` (x1, y1, x2, y2) out of `frame`, clamped to frame bounds.

    Returns None if the clamped crop is degenerate (off-frame or too small
    to build a meaningful histogram from) instead of raising.
    """
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    x1c, y1c = max(0, int(x1)), max(0, int(y1))
    x2c, y2c = min(width, int(x2)), min(height, int(y2))
    if x2c - x1c < MIN_CROP_DIMENSION or y2c - y1c < MIN_CROP_DIMENSION:
        return None
    return frame[y1c:y2c, x1c:x2c]


def compute_embedding(
    frame: np.ndarray, bbox: tuple[float, float, float, float]
) -> list[float] | None:
    """A lightweight appearance descriptor for cross-session cat re-identification.

    This is deliberately NOT a learned embedding model -- it's a normalized
    HSV color histogram of the detected cat's crop. That is enough to tell
    apart cats with visibly different coat colors/patterns in a small,
    single-camera home deployment, persisted per Cat row (see
    app.cats.models.Cat.embedding) and compared with `cosine_similarity`
    below so a cat keeps the same identity across process restarts and
    across the tracker losing/reacquiring it mid-session -- unlike the raw
    CentroidTracker track_id, which is an in-memory counter that resets on
    every restart.

    Known limitation: it will NOT reliably distinguish two cats that look
    almost identical (e.g. two solid-black cats of similar size). Swap this
    out for a learned appearance-embedding model if that becomes a problem
    -- everything downstream (CatRepository/CatService matching) only
    depends on cosine_similarity(list[float], list[float]) behaving
    consistently, not on how the vector is produced.

    Returns None (instead of a zero/garbage vector) when the crop is too
    degenerate to trust, so callers can fall back to track-id-only
    resolution for that single observation rather than poisoning a cat's
    stored embedding with noise.
    """
    crop = crop_bbox(frame, bbox)
    if crop is None:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, list(EMBEDDING_BINS), [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist, hist, alpha=0.0, beta=1.0, norm_type=cv2.NORM_MINMAX)
    return [float(v) for v in hist.flatten()]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [-1, 1] (in practice [0, 1] for these
    non-negative histogram vectors). Returns 0.0 for a degenerate
    (all-zero) vector instead of raising a divide-by-zero.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def running_average(
    existing: list[float], existing_samples: int, new: list[float], max_samples: int = 50
) -> list[float]:
    """Blends a new observation into a running-average embedding so a cat's
    stored appearance adapts over time (different lighting, poses) without
    letting any single noisy frame overwrite it outright.

    `max_samples` caps the effective averaging window so the embedding stays
    adaptable indefinitely rather than freezing solid after a long uptime.
    """
    n = min(existing_samples, max_samples)
    return [(o * n + e) / (n + 1) for o, e in zip(existing, new, strict=True)]
