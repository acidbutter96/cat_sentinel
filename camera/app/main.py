"""FastAPI app instance: logging setup, middleware, exception handlers,
routers, and the lifespan that owns the single shared RTSPCamera connection
and the recordings reconciliation background task.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.camera.router import router as camera_router
from app.camera.service import RTSPCamera
from app.core.exceptions import register_exception_handlers
from app.db.session import AsyncSessionLocal
from app.events.camera_command_dispatcher import TapoCameraCommandDispatcher
from app.events.router import router as events_router
from app.ptz.router import router as ptz_router
from app.ptz.service import PTZController
from app.recordings.router import router as recordings_router
from app.recordings.service import run_reconciliation_loop
from app.settings.config import settings
from app.settings.logging_config import setup_logging
from app.settings.middleware import register_middleware
from app.webhooks.router import router as webhooks_router

setup_logging(settings.log_level)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    camera = RTSPCamera(settings.camera_rtsp_url, settings.camera_rtsp_transport)
    camera.start()
    app.state.camera = camera

    # PTZController's constructor makes a blocking probe request to the
    # camera (pytapo's KLAP-vs-legacy protocol detection) -- run it off the
    # event loop so an unreachable camera doesn't stall app startup.
    ptz_controller = await asyncio.to_thread(
        PTZController,
        settings.camera_host,
        settings.tapo_control_user,
        settings.tapo_control_password,
        settings.ptz_units_per_degree,
    )
    app.state.ptz_controller = ptz_controller
    app.state.command_dispatcher = TapoCameraCommandDispatcher(ptz_controller)

    reconciliation_task = asyncio.create_task(
        run_reconciliation_loop(settings.recording_scan_interval_seconds, AsyncSessionLocal)
    )

    try:
        yield
    finally:
        reconciliation_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reconciliation_task
        camera.stop()


app = FastAPI(
    title="jortan-camera-api",
    description="RTSP-to-HTTP bridge and PTZ control for the TP-Link Tapo C200 IP camera.",
    lifespan=lifespan,
)

register_middleware(app)
register_exception_handlers(app)

app.include_router(camera_router)
app.include_router(recordings_router)
app.include_router(events_router)
app.include_router(webhooks_router)
app.include_router(ptz_router)


@app.get("/health", tags=["meta"], summary="Liveness check")
async def health() -> dict[str, str]:
    return {"status": "ok"}
