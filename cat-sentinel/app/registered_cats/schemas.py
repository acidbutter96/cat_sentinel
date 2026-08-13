import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.registered_cats.models import CatSex


class RegisteredCatCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None
    sex: CatSex = CatSex.UNKNOWN
    description: str | None = Field(default=None, max_length=2_000)
    detected_cat_id: uuid.UUID | None = None


class RegisteredCatUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    sex: CatSex | None = None
    description: str | None = Field(default=None, max_length=2_000)
    detected_cat_id: uuid.UUID | None = None


class RegisteredCatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    detected_cat_id: uuid.UUID | None
    name: str
    birth_date: date | None
    sex: CatSex
    description: str | None
    photo_path: str | None
    created_at: datetime
    updated_at: datetime
