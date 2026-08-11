import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, times the request, and logs one line per request.

    This applies to literally every request (including 404s and unhandled
    errors), which is why it's middleware rather than a dependency.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request %s failed: %s %s", request_id, request.method, request.url.path
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


def register_middleware(app) -> None:
    """Mirrors register_exception_handlers(app) -- keeps main.py a short list
    of registration calls instead of inline app.add_middleware(...) clutter.
    """
    app.add_middleware(RequestContextMiddleware)
