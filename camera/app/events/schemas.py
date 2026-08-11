from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EventTrigger(BaseModel):
    """Payload posted by cat-sentinel (or any other detection source) to
    POST /events/trigger.
    """

    event_type: str = Field(..., description="e.g. 'cat_detected', 'intruder_detected'")
    camera_id: str = Field(..., description="Identifier of the camera that produced the event")
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventRecord(BaseModel):
    """A logged event, as returned by GET /events."""

    event_type: str
    camera_id: str
    metadata: dict[str, Any]
    timestamp: datetime
    command_dispatched: str | None
    command_success: bool | None


class EventTriggerResult(BaseModel):
    accepted: bool
    command_dispatched: str | None
    command_success: bool | None
    webhooks_notified: int


class CommandMapping(BaseModel):
    event_type: str
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class CommandMappingUpsert(BaseModel):
    command: str
    params: dict[str, Any] = Field(default_factory=dict)
