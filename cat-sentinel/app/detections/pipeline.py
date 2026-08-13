from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from app.activities.models import ActivityKind
from app.activities.repository import ActivityRepository
from app.activities.schemas import ActivityCreate
from app.activities.service import ActivityService
from app.alerts.models import AlertKind
from app.alerts.repository import AlertRepository
from app.alerts.service import AlertCooldownTracker, AlertService
from app.cats.repository import CatRepository
from app.cats.service import CatService
from app.db.session import async_session_factory
from app.detections.repository import DetectionRepository
from app.detections.schemas import Centroid, DetectionCreate
from app.detections.service import DetectionService
from app.registered_cats.repository import RegisteredCatRepository
from app.registered_cats.service import RegisteredCatService
from app.settings.config import settings
from app.streaming.client import RatSentinelStreamClient
from app.streaming.frame_source import FrameSource
from app.vision.detector import YoloCatDetector
from app.vision.reid import compute_embedding
from app.vision.snapshots import save_cat_snapshot, save_entry_frame
from app.vision.tracker import CentroidTracker
from app.zones.repository import ZoneRepository
from app.zones.service import ZoneService, point_in_polygon

logger = logging.getLogger(__name__)

# Sentinel "zone" key for AlertCooldownTracker so camera-entry alerts (which
# have no real zone_id) get their own cooldown bucket instead of colliding
# with a real zone UUID.
_CAMERA_ENTRY_COOLDOWN_KEY = uuid.UUID(int=0)


class DetectionPipeline:
    """Pulls frames from the upstream camera, detects and tracks cats,
    persists observations, and fires danger-zone alerts.

    Runs as a background task started (but not owned/blocked-on) by FastAPI's
    lifespan startup -- see app.main.
    """

    def __init__(
        self,
        camera_id: str | None = None,
        stream_url: str | None = None,
    ):
        self.camera_id = camera_id or settings.camera_id
        self.stream_client = RatSentinelStreamClient(stream_url or settings.camera_stream_url)
        self.frame_source = FrameSource(self.stream_client)
        self.detector = YoloCatDetector()
        self.tracker = CentroidTracker()
        self.cooldown_tracker = AlertCooldownTracker()
        self.entry_cooldown_tracker = AlertCooldownTracker(settings.alert_entry_cooldown_seconds)
        self._stop_event = asyncio.Event()
        # Per-process cache of tracker track_id -> resolved persistent Cat.id
        # for this pipeline run. Lets repeat observations of the same track
        # skip the appearance-search in CatService.identify_or_create (see
        # CatService.touch) and lets us detect "this track_id is new" to
        # decide when to fire a camera-entry alert -- see _process_frame.
        self._track_to_cat: dict[int, uuid.UUID] = {}

    def stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        """Main pipeline loop.

        Deliberately NOT decorated with @log_call/@log_errors: this is a
        hot-path, long-running loop that must survive a per-frame exception
        without killing the whole background task (a single bad frame, a
        transient DB error, or a webhook timeout should not take down cat
        detection entirely). The broad except below is intentional for that
        reason -- log and continue, rather than let one failure propagate
        and end run_forever() for good.
        """
        logger.info("detection pipeline starting for camera_id=%s", self.camera_id)
        while not self._stop_event.is_set():
            try:
                async for frame in self.frame_source.frames():
                    if self._stop_event.is_set():
                        break
                    await self._process_frame(frame)
            except Exception:
                logger.exception("detection pipeline stream loop failed, reconnecting shortly")
                await asyncio.sleep(2.0)

    async def _process_frame(self, frame) -> None:
        try:
            raw_detections = self.detector.detect(frame)
            tracked = self.tracker.update([(d.bbox, d.centroid) for d in raw_detections])

            async with async_session_factory() as session:
                cat_service = CatService(CatRepository(session))
                zone_service = ZoneService(ZoneRepository(session))
                detection_service = DetectionService(DetectionRepository(session))
                alert_service = AlertService(AlertRepository(session))
                activity_service = ActivityService(ActivityRepository(session))
                registered_cat_service = RegisteredCatService(RegisteredCatRepository(session))

                zones = await zone_service.list_active_for_camera(self.camera_id)

                for track_id, tracked_obj in tracked.items():
                    embedding = compute_embedding(frame, tracked_obj.bbox)

                    # A track_id this pipeline process hasn't resolved yet --
                    # either a genuinely new cat, or a known cat re-entering
                    # frame after leaving (the tracker aged the old track
                    # out) or a process restart (CentroidTracker's counter
                    # restarted from 1). Either way, from the camera's point
                    # of view this IS a fresh entry into its field of view.
                    is_new_track = track_id not in self._track_to_cat
                    if is_new_track:
                        registered_cat = await registered_cat_service.find_best_match(embedding)
                        cat = await cat_service.identify_or_create(
                            self.camera_id,
                            track_id,
                            embedding,
                            registered_cat_id=registered_cat.id if registered_cat else None,
                            registered_cat_name=registered_cat.name if registered_cat else None,
                        )
                        self._track_to_cat[track_id] = cat.id
                    else:
                        cat = await cat_service.touch(self._track_to_cat[track_id], embedding)

                    if is_new_track and self.entry_cooldown_tracker.should_fire(
                        cat.id, _CAMERA_ENTRY_COOLDOWN_KEY
                    ):
                        await alert_service.fire(
                            cat.id,
                            self.camera_id,
                            kind=AlertKind.CAMERA_ENTRY,
                        )
                        self.entry_cooldown_tracker.mark_fired(cat.id, _CAMERA_ENTRY_COOLDOWN_KEY)
                        await activity_service.record(
                            ActivityCreate(
                                camera_id=self.camera_id,
                                cat_id=cat.id,
                                kind=ActivityKind.ENTERED_FRAME,
                                message=f"{cat.label} entered the camera's field of view",
                            )
                        )

                    matched_zone_id = None
                    in_danger_zone = False
                    for zone in zones:
                        polygon = [(p["x"], p["y"]) for p in zone.points]
                        if point_in_polygon(tracked_obj.centroid, polygon):
                            in_danger_zone = True
                            matched_zone_id = zone.id
                            break

                    confidence = next(
                        (d.confidence for d in raw_detections if d.bbox == tracked_obj.bbox), 0.0
                    )

                    snapshot_path = None
                    frame_path = None
                    captured_at = datetime.now(UTC)
                    if is_new_track:
                        try:
                            snapshot_path = await asyncio.to_thread(
                                save_cat_snapshot,
                                frame,
                                tracked_obj.bbox,
                                output_dir=settings.snapshot_dir,
                                camera_id=self.camera_id,
                                cat_id=cat.id,
                                captured_at=captured_at,
                            )
                            frame_path = await asyncio.to_thread(
                                save_entry_frame,
                                frame,
                                output_dir=settings.snapshot_dir,
                                camera_id=self.camera_id,
                                cat_id=cat.id,
                                captured_at=captured_at,
                            )
                        except Exception:
                            logger.exception(
                                "failed to save selection images for cat_id=%s",
                                cat.id,
                            )

                    await detection_service.create(
                        DetectionCreate(
                            cat_id=cat.id,
                            camera_id=self.camera_id,
                            track_id=track_id,
                            zone_id=matched_zone_id,
                            bbox=list(tracked_obj.bbox),
                            centroid=Centroid(x=tracked_obj.centroid[0], y=tracked_obj.centroid[1]),
                            in_danger_zone=in_danger_zone,
                            confidence=confidence,
                            snapshot_path=snapshot_path,
                            frame_path=frame_path,
                            timestamp=captured_at,
                        )
                    )
                    await activity_service.record(
                        ActivityCreate(
                            camera_id=self.camera_id,
                            cat_id=cat.id,
                            kind=ActivityKind.DETECTION,
                            message=f"{cat.label} detected"
                            + (f" in zone {matched_zone_id}" if in_danger_zone else ""),
                        )
                    )

                    if (
                        in_danger_zone
                        and matched_zone_id is not None
                        and self.cooldown_tracker.should_fire(cat.id, matched_zone_id)
                    ):
                        alert = await alert_service.fire(
                            cat.id,
                            self.camera_id,
                            kind=AlertKind.DANGER_ZONE,
                            zone_id=matched_zone_id,
                        )
                        self.cooldown_tracker.mark_fired(cat.id, matched_zone_id)
                        await activity_service.record(
                            ActivityCreate(
                                camera_id=self.camera_id,
                                cat_id=cat.id,
                                kind=ActivityKind.ALERT,
                                message=f"Alert fired for {cat.label} entering danger zone "
                                f"(status={alert.status.value})",
                            )
                        )

                # Drop cache entries for tracks CentroidTracker has aged out
                # so the cache doesn't grow unboundedly over a long-running
                # process, and so a future reuse of that same track_id number
                # goes through identify_or_create's appearance search again
                # rather than trusting a stale mapping.
                self._track_to_cat = {
                    tid: cat_id for tid, cat_id in self._track_to_cat.items() if tid in tracked
                }

        except Exception:
            # Deliberate broad catch -- see the run_forever() docstring.
            logger.exception("failed to process a frame, continuing to next frame")
