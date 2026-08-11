from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.recordings.models import Recording, RecordingStatus


class RecordingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, filename: str) -> Recording:
        recording = Recording(filename=filename, status=RecordingStatus.RECORDING)
        self.session.add(recording)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(f"A recording named {filename!r} already exists") from exc
        await self.session.refresh(recording)
        return recording

    async def get_by_filename(self, filename: str) -> Recording | None:
        result = await self.session.execute(
            select(Recording).where(Recording.filename == filename)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, recording_id: uuid.UUID) -> Recording | None:
        result = await self.session.execute(select(Recording).where(Recording.id == recording_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Recording]:
        result = await self.session.execute(select(Recording).order_by(Recording.started_at.desc()))
        return list(result.scalars().all())

    async def mark_completed(
        self,
        recording: Recording,
        ended_at: datetime,
        duration_seconds: float,
        file_size_bytes: int | None,
    ) -> Recording:
        recording.ended_at = ended_at
        recording.duration_seconds = duration_seconds
        recording.file_size_bytes = file_size_bytes
        recording.status = RecordingStatus.COMPLETED
        await self.session.commit()
        await self.session.refresh(recording)
        return recording

    async def mark_status(self, recording: Recording, status: RecordingStatus) -> Recording:
        recording.status = status
        await self.session.commit()
        await self.session.refresh(recording)
        return recording

    async def update_file_size(self, recording: Recording, file_size_bytes: int) -> Recording:
        recording.file_size_bytes = file_size_bytes
        await self.session.commit()
        await self.session.refresh(recording)
        return recording
