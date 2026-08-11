"""Global middleware: request id, timing, and one log line per request.

This is the deliberate exception to "prefer dependencies over middleware" --
these concerns must run for literally every request (including 404s and
unhandled errors), so they can't be scoped to individual routes via Depends.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.request")

# Contextvar so the current request id is reachable from anywhere (e.g. a
# logging filter) without threading it through every function signature.
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id (from X-Request-ID if provided, else generated),
    times the request, and logs one line per request.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
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
        finally:
            _request_id_ctx.reset(token)


def register_middleware(app) -> None:
    """Mirrors register_exception_handlers(app) -- keeps main.py a short list
    of registration calls instead of inline app.add_middleware(...) clutter.
    """
    app.add_middleware(RequestContextMiddleware)
