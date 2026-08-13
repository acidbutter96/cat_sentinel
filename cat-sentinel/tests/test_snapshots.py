import uuid
from datetime import UTC, datetime

import cv2
import numpy as np

from app.vision.snapshots import save_cat_snapshot, save_entry_frame


def test_save_cat_snapshot_writes_padded_cat_crop(tmp_path):
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    frame[20:80, 30:90] = (0, 128, 255)
    cat_id = uuid.uuid4()

    path = save_cat_snapshot(
        frame,
        (30, 20, 90, 80),
        output_dir=str(tmp_path),
        camera_id="default",
        cat_id=cat_id,
    )

    assert path is not None
    saved = cv2.imread(path)
    assert saved is not None
    assert saved.shape[0] > 60
    assert saved.shape[1] > 60
    assert str(cat_id) in path


def test_save_entry_frame_writes_the_full_camera_frame(tmp_path):
    frame = np.full((100, 120, 3), 127, dtype=np.uint8)
    path = save_entry_frame(
        frame,
        output_dir=str(tmp_path),
        camera_id="default",
        cat_id=uuid.uuid4(),
        captured_at=datetime.now(UTC),
    )

    saved = cv2.imread(path)
    assert saved is not None
    assert saved.shape[:2] == frame.shape[:2]
    assert path.endswith("_frame.jpg")
