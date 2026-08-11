from __future__ import annotations

import asyncio
import logging

from app.activities.models import ActivityKind
from app.activities.repository import ActivityRepository
from app.activities.schemas import ActivityCreate
from app.activities.service import ActivityService
from app.alerts.repository import AlertRepository
from app.alerts.service import AlertCooldownTracker, AlertService
from app.cats.repository import CatRepository
from app.cats.service import CatService
from app.db.session import async_session_factory
from app.detections.repository import DetectionRepository
from app.detections.schemas import Centroid, DetectionCreate
from app.detections.service import DetectionService
from app.settings.config import settings
from app.streaming.broadcaster import AnnotatedFrameBroadcaster
from app.streaming.client import RatSentinelStreamClient
from app.streaming.frame_source import FrameSource
from app.vision.annotator import FrameAnnotator
from app.vision.detector import YoloCatDetector
from app.vision.tracker import CentroidTracker
from app.zones.repository import ZoneRepository
from app.zones.service import ZoneService, point_in_polygon

logger = logging.getLogger(__name__)


class DetectionPipeline:
    """Pulls frames from the upstream camera, detects and tracks cats,
    persists observations, fires danger-zone alerts, and publishes
    annotated frames for the MJPEG stream endpoint.

    Runs as a background task started (but not owned/blocked-on) by
    FastAPI's lifespan startup -- see app.main. It is NOT the source of
    `app.state.broadcaster`, which must exist before the pipeline starts (or
    even before it's able to start) so routes never see a missing
    broadcaster.
    """

    def __init__(
        self,
        broadcaster: AnnotatedFrameBroadcaster,
        camera_id: str | None = None,
        stream_url: str | None = None,
    ):
        self.broadcaster = broadcaster
        self.camera_id = camera_id or settings.camera_id
        self.stream_client = RatSentinelStreamClient(stream_url or settings.camera_stream_url)
        self.frame_source = FrameSource(self.stream_client)
        self.detector = YoloCatDetector()
        self.tracker = CentroidTracker()
        self.annotator = FrameAnnotator()
        self.cooldown_tracker = AlertCooldownTracker()
        self._stop_event = asyncio.Event()

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

                zones = await zone_service.list_active_for_camera(self.camera_id)

                boxes_to_draw: list[tuple[tuple[float, float, float, float], str, bool]] = []

                for track_id, tracked_obj in tracked.items():
                    cat = await cat_service.get_or_create_for_track(self.camera_id, track_id)

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

                    await detection_service.create(
                        DetectionCreate(
                            cat_id=cat.id,
                            camera_id=self.camera_id,
                            zone_id=matched_zone_id,
                            bbox=list(tracked_obj.bbox),
                            centroid=Centroid(x=tracked_obj.centroid[0], y=tracked_obj.centroid[1]),
                            in_danger_zone=in_danger_zone,
                            confidence=confidence,
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

                    if in_danger_zone and matched_zone_id is not None:
                        if self.cooldown_tracker.should_fire(cat.id, matched_zone_id):
                            alert = await alert_service.fire(
                                cat.id, matched_zone_id, self.camera_id
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

                    boxes_to_draw.append(
                        (tracked_obj.bbox, f"{cat.label} #{track_id}", in_danger_zone)
                    )

            annotated_frame = self.annotator.annotate(frame, boxes_to_draw)
            jpeg_bytes = self.annotator.encode_jpeg(annotated_frame)
            await self.broadcaster.publish(jpeg_bytes)
        except Exception:
            # Deliberate broad catch -- see the run_forever() docstring.
            logger.exception("failed to process a frame, continuing to next frame")
