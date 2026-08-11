from app.vision.tracker import CentroidTracker


def test_new_detection_gets_a_new_track_id():
    tracker = CentroidTracker(max_distance=50, max_age_frames=5)
    tracked = tracker.update([((0, 0, 10, 10), (5.0, 5.0))])
    assert len(tracked) == 1
    assert 1 in tracked


def test_matching_centroid_keeps_same_track_id_across_frames():
    tracker = CentroidTracker(max_distance=50, max_age_frames=5)
    tracker.update([((0, 0, 10, 10), (5.0, 5.0))])
    tracked = tracker.update([((2, 2, 12, 12), (7.0, 7.0))])  # moved a little
    assert len(tracked) == 1
    assert 1 in tracked
    assert tracked[1].centroid == (7.0, 7.0)


def test_far_away_detection_gets_new_track_id():
    tracker = CentroidTracker(max_distance=10, max_age_frames=5)
    tracker.update([((0, 0, 10, 10), (5.0, 5.0))])
    tracked = tracker.update([((500, 500, 510, 510), (505.0, 505.0))])
    # Old track ages (no match), new track created for the far detection.
    assert 2 in tracked
    assert tracked[2].centroid == (505.0, 505.0)


def test_track_ages_out_after_max_age_frames_unseen():
    tracker = CentroidTracker(max_distance=50, max_age_frames=2)
    tracker.update([((0, 0, 10, 10), (5.0, 5.0))])
    assert 1 in tracker.objects

    tracker.update([])  # unseen frame 1
    assert 1 in tracker.objects
    tracker.update([])  # unseen frame 2
    assert 1 in tracker.objects
    tracker.update([])  # unseen frame 3 -- exceeds max_age_frames=2
    assert 1 not in tracker.objects


def test_multiple_detections_match_nearest_tracks():
    tracker = CentroidTracker(max_distance=50, max_age_frames=5)
    tracker.update([((0, 0, 10, 10), (5.0, 5.0)), ((100, 100, 110, 110), (105.0, 105.0))])
    tracked = tracker.update(
        [((3, 3, 13, 13), (8.0, 8.0)), ((102, 102, 112, 112), (107.0, 107.0))]
    )
    assert len(tracked) == 2
    # Nearest-neighbor matching should keep IDs 1 and 2 assigned to the
    # cluster they started closest to.
    assert tracked[1].centroid == (8.0, 8.0)
    assert tracked[2].centroid == (107.0, 107.0)
