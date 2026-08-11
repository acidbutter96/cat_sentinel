"""Cross-domain dependency providers only -- the DB session, API-key auth,
the shared RTSPCamera instance, and the camera command dispatcher. Anything
that has to import a specific domain's service/repository to build itself
(e.g. RecordingServiceDep) belongs in that domain's own router.py instead,
to avoid import cycles -- see the fastapi-builder skill notes on DI scope.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.db.session import get_db_session
from app.events.camera_command_dispatcher import (
    CameraCommandDispatcher,
    LoggingCameraCommandDispatcher,
)
from app.settings.config import settings

# --- Database ----------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# --- Auth ----------------------------------------------------------------------


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """No-op (allows all) unless EVENTS_API_KEY is configured, in which case
    it checks the X-API-Key header and raises UnauthorizedError on mismatch.
    """
    if not settings.events_api_key:
        return
    if x_api_key != settings.events_api_key:
        raise UnauthorizedError("Missing or invalid X-API-Key header")


RequireApiKey = Annotated[None, Depends(require_api_key)]


# --- Shared RTSPCamera instance -----------------------------------------------


def get_camera(request: Request):
    """The single RTSPCamera instance lives on app.state, created once at
    startup (see app.main lifespan) and reused by every request -- this
    camera hardware has previously been damaged by too many simultaneous
    RTSP connections, so every domain that needs frames or control reads
    from this one shared instance rather than opening its own connection.
    """
    return request.app.state.camera


CameraDep = Annotated[object, Depends(get_camera)]


# --- Shared PTZController instance --------------------------------------------


def get_ptz_controller(request: Request):
    """The single PTZController instance lives on app.state, created once at
    startup (see app.main lifespan) alongside the RTSPCamera -- same
    one-connection-per-process rationale.
    """
    return request.app.state.ptz_controller


PTZControllerDep = Annotated[object, Depends(get_ptz_controller)]


# --- Camera command dispatcher ------------------------------------------------

# Built once at startup (see app.main lifespan) so it can wrap the shared
# PTZController for ptz_* commands -- see app/events/camera_command_dispatcher.py.
# Fallback below covers requests served without the lifespan having run
# (e.g. ASGI test clients that construct AsyncClient without a lifespan
# manager) -- matches the module-singleton behavior this replaced.
_fallback_dispatcher: CameraCommandDispatcher = LoggingCameraCommandDispatcher()


def get_camera_command_dispatcher(request: Request) -> CameraCommandDispatcher:
    return getattr(request.app.state, "command_dispatcher", _fallback_dispatcher)


CameraCommandDispatcherDep = Annotated[
    CameraCommandDispatcher, Depends(get_camera_command_dispatcher)
]
