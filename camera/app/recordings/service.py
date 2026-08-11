"""Recording metadata business logic, plus the background reconciliation
scheduler that keeps DB rows honest against what's actually on disk.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.decorators import log_errors
from app.core.exceptions import NotFoundError
from app.recordings.models import Recording, RecordingStatus
from app.recordings.repository import RecordingRepository
from app.recordings.schemas import RecordingRead

logger = logging.getLogger(__name__)


def recordings_dir() -> Path:
    from app.settings.config import settings

    path = Path(settings.recordings_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_filename() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"recording_{stamp}_{uuid.uuid4().hex[:8]}.mp4"


@log_errors
class RecordingService:
    def __init__(self, repository: RecordingRepository):
        self.repository = repository

    async def start(self, filename: str) -> Recording:
        return await self.repository.create(filename)

    async def stop(self, filename: str) -> Recording:
        recording = await self.repository.get_by_filename(filename)
        if recording is None:
            raise NotFoundError(f"No recording named {filename!r}")
        path = recordings_dir() / filename
        file_size = path.stat().st_size if path.exists() else None
        ended_at = datetime.now(UTC)
        started_at = recording.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        duration = (ended_at - started_at).total_seconds()
        return await self.repository.mark_completed(recording, ended_at, duration, file_size)

    async def list_all(self) -> list[RecordingRead]:
        recordings = await self.repository.list_all()
        return [RecordingRead.model_validate(r) for r in recordings]

    async def get_file_path(self, filename: str) -> Path:
        recording = await self.repository.get_by_filename(filename)
        if recording is None:
            raise NotFoundError(f"No recording named {filename!r}")
        path = recordings_dir() / filename
        if not path.exists():
            raise NotFoundError(f"Recording file {filename!r} is missing from disk")
        return path

    async def reconcile(self) -> None:
        """Reconciles DB rows against files actually present on disk:
        - a COMPLETED/RECORDING row whose file is gone on disk -> MISSING
        - a RECORDING row whose file exists but is stale (no active writer
          tracked -- best-effort, based on file mtime) is left alone here;
          actual "is a recording still active" truth lives in
          app.camera.service.RTSPCamera, this only fixes up file-size drift
          and rows pointing at files that no longer exist.
        """
        recordings = await self.repository.list_all()
        directory = recordings_dir()
        for recording in recordings:
            path = directory / recording.filename
            if not path.exists():
                if recording.status != RecordingStatus.MISSING:
                    logger.warning(
                        "recording %s missing from disk, marking MISSING", recording.filename
                    )
                    await self.repository.mark_status(recording, RecordingStatus.MISSING)
                continue

            actual_size = path.stat().st_size
            if recording.file_size_bytes != actual_size and recording.status in (
                RecordingStatus.COMPLETED,
                RecordingStatus.MISSING,
            ):
                await self.repository.update_file_size(recording, actual_size)


async def run_reconciliation_loop(interval_seconds: int, session_factory) -> None:
    """Simple asyncio task, looped forever, run from app startup (see
    app.main lifespan). Owns its own DB session per iteration since it
    outlives any single request.
    """
    while True:
        try:
            async with session_factory() as session:
                service = RecordingService(RecordingRepository(session))
                await service.reconcile()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("recording reconciliation pass failed")
        await asyncio.sleep(interval_seconds)
