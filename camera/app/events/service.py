"""Business logic for the detection-event ingestion pipeline.

Event-type -> command mapping is an in-memory dict (spec explicitly allows
this to be in-memory rather than DB-backed), wrapped here so callers never
touch the dict directly. The recent-event log is a bounded deque, capped at
MAX_EVENTS entries, also in-memory by design (see events/router.py docstring
for why this domain doesn't need durable storage).
"""

from __future__ import annotations

from collections import deque
from typing import Any

from app.core.decorators import log_errors
from app.core.exceptions import NotFoundError
from app.events.camera_command_dispatcher import CameraCommandDispatcher
from app.events.schemas import CommandMapping, EventRecord, EventTrigger

MAX_EVENTS = 500

# Sensible factory defaults -- editable at runtime via the
# GET/PUT/DELETE /events/commands/{event_type} endpoints.
_DEFAULT_COMMAND_MAP: dict[str, dict[str, Any]] = {
    "cat_detected": {"command": "light_on", "params": {"duration_seconds": 30}},
    "intruder_detected": {"command": "siren_on", "params": {"duration_seconds": 10}},
}


@log_errors
class EventCommandMapService:
    """CRUD over the event_type -> command mapping table."""

    def __init__(self) -> None:
        self._mappings: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _DEFAULT_COMMAND_MAP.items()
        }

    async def list_all(self) -> list[CommandMapping]:
        return [
            CommandMapping(event_type=event_type, **mapping)
            for event_type, mapping in self._mappings.items()
        ]

    async def get(self, event_type: str) -> CommandMapping:
        mapping = self._mappings.get(event_type)
        if mapping is None:
            raise NotFoundError(f"No command mapping for event_type={event_type!r}")
        return CommandMapping(event_type=event_type, **mapping)

    async def upsert(self, event_type: str, command: str, params: dict[str, Any]) -> CommandMapping:
        self._mappings[event_type] = {"command": command, "params": params}
        return CommandMapping(event_type=event_type, command=command, params=params)

    async def delete(self, event_type: str) -> None:
        if event_type not in self._mappings:
            raise NotFoundError(f"No command mapping for event_type={event_type!r}")
        del self._mappings[event_type]

    async def resolve(self, event_type: str) -> dict[str, Any] | None:
        """Returns the raw {"command": ..., "params": ...} dict, or None if
        this event_type has no mapping (not an error -- some events are
        purely informational and shouldn't trigger a camera command).
        """
        return self._mappings.get(event_type)


@log_errors
class EventLogService:
    """Bounded in-memory log of recently ingested events."""

    def __init__(self) -> None:
        self._log: deque[EventRecord] = deque(maxlen=MAX_EVENTS)

    async def record(
        self,
        trigger: EventTrigger,
        command_dispatched: str | None,
        command_success: bool | None,
    ) -> None:
        self._log.appendleft(
            EventRecord(
                event_type=trigger.event_type,
                camera_id=trigger.camera_id,
                metadata=trigger.metadata,
                timestamp=trigger.timestamp,
                command_dispatched=command_dispatched,
                command_success=command_success,
            )
        )

    async def recent(self, limit: int = 100) -> list[EventRecord]:
        return list(self._log)[:limit]


class EventIngestionService:
    """Orchestrates a single POST /events/trigger call: resolve command,
    dispatch it, log the event, and fan out to webhook subscribers.

    Not decorated with @log_errors -- its one method already logs via the
    services/dispatcher it calls, and it needs a plain try/except around the
    webhook fan-out specifically so a webhook failure can never affect the
    response to the original caller.
    """

    def __init__(
        self,
        command_map_service: EventCommandMapService,
        log_service: EventLogService,
        dispatcher: CameraCommandDispatcher,
        webhook_fanout,
    ) -> None:
        self.command_map_service = command_map_service
        self.log_service = log_service
        self.dispatcher = dispatcher
        # Callable[[EventTrigger], Awaitable[int]] -- injected rather than
        # imported at module scope so this service doesn't hard-depend on
        # the webhooks domain's internal storage layout, only its service
        # function signature.
        self.webhook_fanout = webhook_fanout

    async def ingest(self, trigger: EventTrigger) -> tuple[str | None, bool | None, int]:
        mapping = await self.command_map_service.resolve(trigger.event_type)

        command_dispatched: str | None = None
        command_success: bool | None = None
        if mapping is not None:
            command_dispatched = mapping["command"]
            command_success = self.dispatcher.dispatch(mapping["command"], mapping["params"])

        await self.log_service.record(trigger, command_dispatched, command_success)

        # Webhook fan-out is best-effort and must never fail this request.
        try:
            notified = await self.webhook_fanout(trigger)
        except Exception:  # noqa: BLE001 -- deliberate: never let fan-out break ingest
            import logging

            logging.getLogger(__name__).exception(
                "webhook fan-out raised unexpectedly for event_type=%s", trigger.event_type
            )
            notified = 0

        return command_dispatched, command_success, notified
