from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl
    event_types: list[str] | None = Field(
        default=None, description="If set, only these event_types are delivered to this webhook."
    )


class WebhookSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    event_types: list[str] | None
