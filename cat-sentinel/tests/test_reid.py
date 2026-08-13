import numpy as np

from app.vision.reid import compute_embedding, cosine_similarity, crop_bbox, running_average


def _solid_color_frame(color: tuple[int, int, int], size: int = 40) -> np.ndarray:
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:, :] = color
    return frame


def test_crop_bbox_clamps_to_frame_bounds():
    frame = _solid_color_frame((0, 0, 0), size=20)
    crop = crop_bbox(frame, (-5, -5, 15, 15))
    assert crop is not None
    assert crop.shape[0] == 15
    assert crop.shape[1] == 15


def test_crop_bbox_returns_none_for_degenerate_box():
    frame = _solid_color_frame((0, 0, 0), size=20)
    assert crop_bbox(frame, (5, 5, 6, 6)) is None
    assert crop_bbox(frame, (100, 100, 110, 110)) is None


def test_compute_embedding_returns_none_for_degenerate_box():
    frame = _solid_color_frame((0, 0, 0), size=20)
    assert compute_embedding(frame, (100, 100, 110, 110)) is None


def test_compute_embedding_same_color_crops_are_more_similar_than_different_ones():
    orange_frame = _solid_color_frame((0, 140, 255))  # BGR "orange"
    orange_frame_2 = _solid_color_frame((10, 150, 250))  # slightly different orange
    black_frame = _solid_color_frame((10, 10, 10))

    bbox = (5, 5, 35, 35)
    emb_orange = compute_embedding(orange_frame, bbox)
    emb_orange_2 = compute_embedding(orange_frame_2, bbox)
    emb_black = compute_embedding(black_frame, bbox)

    assert emb_orange is not None
    assert emb_orange_2 is not None
    assert emb_black is not None

    same_cat_score = cosine_similarity(emb_orange, emb_orange_2)
    different_cat_score = cosine_similarity(emb_orange, emb_black)
    assert same_cat_score > different_cat_score


def test_cosine_similarity_identical_vectors_is_one():
    vec = [1.0, 2.0, 3.0]
    assert cosine_similarity(vec, vec) == 1.0


def test_cosine_similarity_handles_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_similarity_mismatched_lengths_returns_zero():
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


def test_running_average_blends_toward_new_observation():
    existing = [0.0, 0.0]
    updated = running_average(existing, existing_samples=1, new=[2.0, 4.0])
    # (0*1 + 2)/2 = 1.0, (0*1 + 4)/2 = 2.0
    assert updated == [1.0, 2.0]


def test_running_average_caps_effective_window():
    existing = [10.0]
    # With max_samples=2, samples beyond that stop diluting the update.
    updated_uncapped = running_average(existing, existing_samples=1000, new=[0.0], max_samples=1000)
    updated_capped = running_average(existing, existing_samples=1000, new=[0.0], max_samples=2)
    assert updated_capped[0] > updated_uncapped[0]
