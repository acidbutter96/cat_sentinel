"""Domain exceptions + a self-registering exception-handler registry.

Adding a new domain error later means: define the exception class, decorate
a handler function right below it. Nothing else to remember -- main.py picks
every handler up via register_exception_handlers(app).
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, status
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


class NotFoundError(Exception):
    def __init__(self, detail: str = "Resource not found"):
        self.detail = detail


class UpstreamServiceError(Exception):
    """Raised when an upstream service (cat-sentinel, camera) is unreachable
    or returns an error. Mapped to HTTP 502 -- never let a raw httpx
    ConnectError/TimeoutException leak to the client uncaught.
    """

    def __init__(self, detail: str = "Upstream service unavailable"):
        self.detail = detail


@exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.detail})


@exception_handler(UpstreamServiceError)
async def handle_upstream_service_error(
    request: Request, exc: UpstreamServiceError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": exc.detail})
