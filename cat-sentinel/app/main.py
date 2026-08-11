import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.activities.router import router as activities_router
from app.alerts.router import router as alerts_router
from app.cats.router import router as cats_router
from app.core.exceptions import register_exception_handlers
from app.detections.pipeline import DetectionPipeline
from app.detections.router import router as detections_router
from app.settings.config import settings
from app.settings.logging_config import setup_logging
from app.settings.middleware import register_middleware
from app.streaming.broadcaster import AnnotatedFrameBroadcaster
from app.streaming.router import router as streaming_router
from app.zones.router import router as zones_router

setup_logging(settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pipeline_task: asyncio.Task | None = None
    if settings.detection_pipeline_enabled:
        pipeline = DetectionPipeline(broadcaster=app.state.broadcaster)
        app.state.pipeline = pipeline
        pipeline_task = asyncio.create_task(pipeline.run_forever())
        logger.info("detection pipeline background task started")
    else:
        logger.info("detection pipeline disabled via settings, not starting")

    yield

    if pipeline_task is not None:
        app.state.pipeline.stop()
        pipeline_task.cancel()
        try:
            await pipeline_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

# app.state.broadcaster is created here, at app-construction time, NOT
# inside lifespan -- routes (GET /stream/annotated) must never see a
# missing broadcaster, even before the detection pipeline has started.
app.state.broadcaster = AnnotatedFrameBroadcaster()

register_middleware(app)
register_exception_handlers(app)

app.include_router(zones_router)
app.include_router(cats_router)
app.include_router(detections_router)
app.include_router(alerts_router)
app.include_router(activities_router)
app.include_router(streaming_router)


@app.get("/health", tags=["meta"], summary="Liveness check")
async def health() -> dict[str, str]:
    return {"status": "ok"}
