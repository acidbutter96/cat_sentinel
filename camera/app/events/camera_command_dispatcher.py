"""Protocol for turning an event-mapped command into an actual camera/actuator
action, plus the implementations that exist today.

KNOWN GAP: siren/light control was never built -- there is no actuator API
for those on the Tapo C200 (it has none itself; that would be an external
relay). LoggingCameraCommandDispatcher just logs what it *would* have done.
TapoCameraCommandDispatcher handles the `ptz_*` commands for real via the
shared PTZController and falls back to a LoggingCameraCommandDispatcher for
everything else. Wiring happens via
app.core.dependencies.get_camera_command_dispatcher (built once at startup
in app.main's lifespan), so nothing in app/events/router.py or
app/events/service.py needs to change.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class CameraCommandDispatcher(Protocol):
    def dispatch(self, command: str, params: dict) -> bool:
        """Executes `command` against the camera/actuators. Returns True on
        (believed) success, False otherwise. Must not raise for expected
        failure modes -- log and return False instead.
        """
        ...


class LoggingCameraCommandDispatcher:
    """Implements CameraCommandDispatcher by only logging. Also used as the
    fallback for any command TapoCameraCommandDispatcher doesn't recognize.
    """

    def dispatch(self, command: str, params: dict) -> bool:
        logger.info(
            "would dispatch camera command %r with params=%r (no-op: logging only)",
            command,
            params,
        )
        return True


class TapoCameraCommandDispatcher:
    """Dispatches `ptz_move` / `ptz_nudge` / `ptz_calibrate` to the shared
    PTZController; everything else falls back to `fallback` (a
    LoggingCameraCommandDispatcher by default). Called synchronously from
    EventIngestionService.ingest, so this method is deliberately sync too --
    pytapo itself is a blocking, `requests`-based client. Detection events
    are low-frequency, so briefly blocking the event loop here is an
    accepted tradeoff rather than a bug (see app/ptz/router.py for the
    to_thread-wrapped, non-blocking path used by direct HTTP callers).
    """

    def __init__(self, ptz, fallback: CameraCommandDispatcher | None = None) -> None:
        self._ptz = ptz
        self._fallback = fallback or LoggingCameraCommandDispatcher()

    def dispatch(self, command: str, params: dict) -> bool:
        try:
            if command == "ptz_move":
                self._ptz.move_to(float(params["pan"]), float(params["tilt"]))
                return True
            if command == "ptz_nudge":
                self._ptz.nudge(float(params["direction"]))
                return True
            if command == "ptz_calibrate":
                self._ptz.calibrate()
                return True
        except Exception:  # noqa: BLE001 -- must not raise, see CameraCommandDispatcher contract
            logger.exception("ptz command %r with params=%r failed", command, params)
            return False

        return self._fallback.dispatch(command, params)
