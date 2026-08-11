from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.settings.config import settings


@dataclass
class TrackedObject:
    track_id: int
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    age_frames_unseen: int = field(default=0)


class CentroidTracker:
    """A simple centroid tracker: matches detections between frame N and
    frame N+1 by nearest Euclidean distance, assigns new IDs when no match
    is found within `max_distance`, and ages out (drops) tracks unseen for
    more than `max_age_frames` consecutive frames.

    Pure, deterministic, no I/O -- easy to unit test without a camera or a
    running detector.
    """

    def __init__(self, max_distance: float | None = None, max_age_frames: int | None = None):
        self.max_distance = (
            max_distance if max_distance is not None else settings.centroid_max_distance
        )
        self.max_age_frames = (
            max_age_frames if max_age_frames is not None else settings.centroid_max_age_frames
        )
        self._next_id = 1
        self.objects: dict[int, TrackedObject] = {}

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def update(
        self, detections: list[tuple[tuple[float, float, float, float], tuple[float, float]]]
    ) -> dict[int, TrackedObject]:
        """`detections` is a list of (bbox, centroid) pairs for the current
        frame. Returns the current {track_id: TrackedObject} mapping after
        matching, creating, and aging out tracks.
        """
        if not detections:
            self._age_unmatched(set(self.objects.keys()))
            return dict(self.objects)

        unmatched_detection_indices = set(range(len(detections)))
        unmatched_track_ids = set(self.objects.keys())

        # Greedy nearest-neighbor matching: repeatedly pick the globally
        # closest (track, detection) pair under the distance threshold.
        candidate_pairs: list[tuple[float, int, int]] = []
        for track_id in unmatched_track_ids:
            track_centroid = self.objects[track_id].centroid
            for det_idx in unmatched_detection_indices:
                _, det_centroid = detections[det_idx]
                dist = self._distance(track_centroid, det_centroid)
                if dist <= self.max_distance:
                    candidate_pairs.append((dist, track_id, det_idx))

        candidate_pairs.sort(key=lambda item: item[0])

        matched_track_ids: set[int] = set()
        matched_detection_indices: set[int] = set()
        for _dist, track_id, det_idx in candidate_pairs:
            if track_id in matched_track_ids or det_idx in matched_detection_indices:
                continue
            bbox, centroid = detections[det_idx]
            self.objects[track_id] = TrackedObject(track_id=track_id, centroid=centroid, bbox=bbox)
            matched_track_ids.add(track_id)
            matched_detection_indices.add(det_idx)

        unmatched_detection_indices -= matched_detection_indices
        unmatched_track_ids -= matched_track_ids

        # Any detection that didn't match an existing track becomes a new one.
        for det_idx in unmatched_detection_indices:
            bbox, centroid = detections[det_idx]
            track_id = self._next_id
            self._next_id += 1
            self.objects[track_id] = TrackedObject(track_id=track_id, centroid=centroid, bbox=bbox)

        self._age_unmatched(unmatched_track_ids)
        return dict(self.objects)

    def _age_unmatched(self, unmatched_track_ids: set[int]) -> None:
        to_drop = []
        for track_id in unmatched_track_ids:
            obj = self.objects[track_id]
            obj.age_frames_unseen += 1
            if obj.age_frames_unseen > self.max_age_frames:
                to_drop.append(track_id)
        for track_id in to_drop:
            del self.objects[track_id]
