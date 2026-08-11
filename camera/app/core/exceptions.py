"""Domain exceptions plus a self-registering exception-handler registry.

Defining a new error type and its HTTP mapping is a two-line change in this
one file -- decorate a handler function with @exception_handler(SomeError)
right below the class, and register_exception_handlers(app) picks it up
automatically. Nothing else in the codebase needs to change.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]
_registry: dict[type[Exception], Handler] = {}


def exception_handler(exc_type: type[Exception]):
    """Decorator that registers a handler function for an exception type."""

    def decorator(func: Handler) -> Handler:
        _registry[exc_type] = func
        return func

    return decorator


def register_exception_handlers(app) -> None:
    for exc_type, handler in _registry.items():
        app.add_exception_handler(exc_type, handler)


# --- Domain exception types -------------------------------------------------


class NotFoundError(Exception):
    def __init__(self, detail: str = "Resource not found"):
        self.detail = detail


class InvalidRequestError(Exception):
    def __init__(self, detail: str = "Invalid request"):
        self.detail = detail


class UnauthorizedError(Exception):
    def __init__(self, detail: str = "Unauthorized"):
        self.detail = detail


class ConflictError(Exception):
    def __init__(self, detail: str = "Conflict"):
        self.detail = detail


class RecordingAlreadyInProgressError(ConflictError):
    def __init__(self, detail: str = "A recording is already in progress"):
        super().__init__(detail)


class FrameNotAvailableError(Exception):
    """Raised by /snapshot or /video when the camera has no decoded frame
    yet (e.g. still connecting, or the connection is down).
    """

    def __init__(self, detail: str = "No frame available from camera yet"):
        self.detail = detail


class PTZDisabledError(Exception):
    """Raised by the PTZ controller dependency when PTZ_ENABLED=false --
    see app.main lifespan and app/core/dependencies.py.
    """

    def __init__(self, detail: str = "PTZ control is disabled (PTZ_ENABLED=false)"):
        self.detail = detail


# --- Handlers ----------------------------------------------------------------


@exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.detail})


@exception_handler(InvalidRequestError)
async def handle_invalid_request(request: Request, exc: InvalidRequestError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.detail})


@exception_handler(UnauthorizedError)
async def handle_unauthorized(request: Request, exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": exc.detail})


@exception_handler(ConflictError)
async def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.detail})


@exception_handler(FrameNotAvailableError)
async def handle_frame_not_available(
    request: Request, exc: FrameNotAvailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": exc.detail}
    )


@exception_handler(PTZDisabledError)
async def handle_ptz_disabled(request: Request, exc: PTZDisabledError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": exc.detail}
    )
