from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.activities.router import router as activities_router
from app.alerts.router import router as alerts_router
from app.cats.router import router as cats_router
from app.core.dependencies import (
    build_camera_stream_client,
    build_cat_sentinel_control_client,
)
from app.core.exceptions import register_exception_handlers
from app.settings.config import settings
from app.settings.logging_config import setup_logging
from app.settings.middleware import register_middleware
from app.snapshots.router import router as snapshots_router
from app.stream.router import router as stream_router
from app.trackers.router import router as trackers_router
from app.zones.router import router as zones_router

setup_logging(settings.log_level, settings.log_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.cat_sentinel_control_client = build_cat_sentinel_control_client()
    app.state.camera_stream_client = build_camera_stream_client()
    try:
        yield
    finally:
        await app.state.cat_sentinel_control_client.aclose()
        await app.state.camera_stream_client.aclose()


app = FastAPI(title="hub", lifespan=lifespan)
register_middleware(app)
register_exception_handlers(app)
app.include_router(trackers_router)
app.include_router(stream_router)
app.include_router(cats_router)
app.include_router(zones_router)
app.include_router(alerts_router)
app.include_router(activities_router)
app.include_router(snapshots_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
