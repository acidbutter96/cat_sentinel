"""Detection-event ingestion -- the "in" half of the event pipeline
(app/webhooks/ is the "out" half).

ARCHITECTURE BOUNDARY (deliberate, not an oversight):
This service does NOT perform any computer vision or ML. Detection itself --
deciding "there is a cat in this frame" or "there is an intruder" -- is
entirely out of scope here. That work lives in a separate microservice,
`cat-sentinel`, which:

  1. polls this service's GET /video (MJPEG) or GET /snapshot to get
     frames, and
  2. runs its own CV/ML models against those frames, and
  3. POSTs its conclusions back here, to POST /events/trigger.

This split was a deliberate past design decision: jortan-camera-api's job is
purely "get video and events on and off a fragile piece of camera hardware
reliably" -- it has no opinion about what's *in* the video. Keeping CV/ML in
a separate process also means a slow/crashing model doesn't take down the
camera bridge, and the bridge doesn't need GPU/ML dependencies at all.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CameraCommandDispatcherDep, RequireApiKey
from app.events.schemas import (
    CommandMapping,
    CommandMappingUpsert,
    EventRecord,
    EventTrigger,
    EventTriggerResult,
)
from app.events.service import EventCommandMapService, EventIngestionService, EventLogService
from app.webhooks.router import get_webhook_service

router = APIRouter(prefix="/events", tags=["events"])

# Process-wide singletons: both are in-memory stores (see service.py), so
# they must persist across requests rather than being rebuilt per-request.
_command_map_service = EventCommandMapService()
_log_service = EventLogService()


def get_command_map_service() -> EventCommandMapService:
    return _command_map_service


def get_log_service() -> EventLogService:
    return _log_service


CommandMapServiceDep = Annotated[EventCommandMapService, Depends(get_command_map_service)]
LogServiceDep = Annotated[EventLogService, Depends(get_log_service)]


def get_ingestion_service(
    command_map_service: CommandMapServiceDep,
    log_service: LogServiceDep,
    dispatcher: CameraCommandDispatcherDep,
) -> EventIngestionService:
    webhook_service = get_webhook_service()
    return EventIngestionService(
        command_map_service=command_map_service,
        log_service=log_service,
        dispatcher=dispatcher,
        webhook_fanout=webhook_service.notify_all,
    )


IngestionServiceDep = Annotated[EventIngestionService, Depends(get_ingestion_service)]


@router.post(
    "/trigger",
    response_model=EventTriggerResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a detection event from cat-sentinel (or any other detector)",
)
async def trigger_event(
    payload: EventTrigger,
    service: IngestionServiceDep,
    _auth: RequireApiKey,
) -> EventTriggerResult:
    command_dispatched, command_success, notified = await service.ingest(payload)
    return EventTriggerResult(
        accepted=True,
        command_dispatched=command_dispatched,
        command_success=command_success,
        webhooks_notified=notified,
    )


@router.get(
    "",
    response_model=list[EventRecord],
    summary="Recent event log (bounded in-memory, most recent first)",
)
async def list_events(service: LogServiceDep, limit: int = 100) -> list[EventRecord]:
    return await service.recent(limit=limit)


@router.get(
    "/commands/{event_type}",
    response_model=CommandMapping,
    summary="Get the camera command mapped to an event_type",
)
async def get_command_mapping(event_type: str, service: CommandMapServiceDep) -> CommandMapping:
    return await service.get(event_type)


@router.put(
    "/commands/{event_type}",
    response_model=CommandMapping,
    summary="Create or replace the camera command mapped to an event_type",
)
async def upsert_command_mapping(
    event_type: str, payload: CommandMappingUpsert, service: CommandMapServiceDep
) -> CommandMapping:
    return await service.upsert(event_type, payload.command, payload.params)


@router.delete(
    "/commands/{event_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove the camera command mapping for an event_type",
)
async def delete_command_mapping(event_type: str, service: CommandMapServiceDep) -> None:
    await service.delete(event_type)
