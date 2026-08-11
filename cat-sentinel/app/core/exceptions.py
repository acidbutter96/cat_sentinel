import math
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]
_registry: dict[type[Exception], Handler] = {}


def exception_handler(exc_type: type[Exception]):
    """Decorator that registers a handler function for an exception type.
    Collect all of these onto the app with register_exception_handlers(app).
    """

    def decorator(func: Handler) -> Handler:
        _registry[exc_type] = func
        return func

    return decorator


def register_exception_handlers(app) -> None:
    for exc_type, handler in _registry.items():
        app.add_exception_handler(exc_type, handler)


# --- Domain exceptions --------------------------------------------------


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


class FrameNotAvailableError(Exception):
    """Raised when no annotated frame is available yet (e.g. the streaming
    broadcaster hasn't received a first frame from the detection pipeline).
    """

    def __init__(self, detail: str = "No frame available"):
        self.detail = detail


# --- Handlers -------------------------------------------------------------


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
async def handle_frame_not_available(request: Request, exc: FrameNotAvailableError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": exc.detail}
    )


def _sanitize(value: Any) -> Any:
    """Recursively replace non-JSON-serializable float values (inf/-inf/nan)
    in an arbitrary structure with their string representation.

    FastAPI's default RequestValidationError handler echoes back the raw
    request body, and json.dumps chokes trying to serialize float('inf') /
    float('nan') (they aren't valid JSON). Zones reject those coordinates at
    the Pydantic-validator level, which means they show up in `body` here --
    so the body must be sanitized before this handler's JSONResponse tries
    to serialize it, or the error response itself would 500.
    """
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            return str(value)
        return value
    if isinstance(value, BaseException):
        # Pydantic v2 puts the raised ValueError itself in errors()[i]["ctx"]["error"],
        # which json.dumps can't serialize -- stringify it.
        return str(value)
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return value


@exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _sanitize(exc.errors()), "body": _sanitize(exc.body)},
    )
