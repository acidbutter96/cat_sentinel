"""Reusable logging decorators shared by every service layer in this app.

log_call wraps *one* function/method (debug on entry, error+traceback on
exception, re-raise unchanged); log_errors is a thin class decorator that
applies log_call to every public method. log_call is the actual primitive --
log_errors loops and delegates to it, it doesn't duplicate its logic.

IMPORTANT hot-path exception: RTSPCamera.get_frame() (app/camera/service.py)
and the MJPEG streaming generator are deliberately NOT decorated with either
of these. They run dozens of times per second on the live-view path, and
entry-logging every single frame would flood the logs and add measurable
overhead to a real-time streaming loop. This is a conscious omission, not a
gap -- see the comment next to those methods.
"""

from __future__ import annotations

import functools
import inspect
import logging


def log_call(func):
    """Logs a debug line before `func` runs and an error line (with
    traceback) if it raises, then re-raises unchanged.

    Only decides *what* gets logged -- formatting/output is entirely owned
    by app.settings.logging_config. Passes structured `extra` fields
    (`event`, `target`) so a JSON formatter can pick them up for free; a
    fixed %-style text format keeps working too since these fields are
    additive, not required by the format string.

    Works on both sync and async functions -- checked once at decoration
    time via inspect.iscoroutinefunction, not on every call.
    """
    log = logging.getLogger(func.__module__)
    qualname = func.__qualname__

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            log.debug("%s called", qualname, extra={"event": "method_call", "target": qualname})
            try:
                return await func(*args, **kwargs)
            except Exception:
                log.exception(
                    "%s failed", qualname, extra={"event": "method_error", "target": qualname}
                )
                raise

        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        log.debug("%s called", qualname, extra={"event": "method_call", "target": qualname})
        try:
            return func(*args, **kwargs)
        except Exception:
            log.exception(
                "%s failed", qualname, extra={"event": "method_error", "target": qualname}
            )
            raise

    return sync_wrapper


def log_errors(cls):
    """Class decorator: applies log_call to every public method of cls."""
    for name, attr in list(vars(cls).items()):
        if name.startswith("_") or not callable(attr):
            continue
        setattr(cls, name, log_call(attr))
    return cls
