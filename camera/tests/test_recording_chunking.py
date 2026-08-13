from __future__ import annotations

import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.recordings.chunking import run_recording_chunk_tick
from app.recordings.repository import RecordingRepository
from tests.fakes import FakeCamera


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    await engine.dispose()


async def test_auto_starts_a_chunk_when_nothing_is_recording(session_factory):
    camera = FakeCamera()
    await run_recording_chunk_tick(camera, session_factory, chunk_seconds=3600, auto_start=True)

    status = camera.get_recording_status()
    assert status.is_recording is True
    assert status.filename is not None

    async with session_factory() as session:
        rows = await RecordingRepository(session).list_all()
        assert len(rows) == 1
        assert rows[0].filename == status.filename


async def test_auto_start_marks_orphaned_open_recordings_failed(session_factory):
    camera = FakeCamera()
    async with session_factory() as session:
        await RecordingRepository(session).create("orphan.mp4")

    await run_recording_chunk_tick(camera, session_factory, chunk_seconds=3600, auto_start=True)

    async with session_factory() as session:
        rows = await RecordingRepository(session).list_all()
        orphan = [row for row in rows if row.filename == "orphan.mp4"][0]
        assert orphan.status.value == "failed"


async def test_does_not_auto_start_when_disabled(session_factory):
    camera = FakeCamera()
    await run_recording_chunk_tick(camera, session_factory, chunk_seconds=3600, auto_start=False)
    assert camera.get_recording_status().is_recording is False


async def test_rotates_into_a_new_chunk_once_elapsed_exceeds_chunk_seconds(session_factory):
    camera = FakeCamera()
    camera.start_recording("chunk_one.mp4", output_dir=None)  # type: ignore[arg-type]
    camera._record_started = time.monotonic() - 9999  # force "elapsed" past the threshold

    async with session_factory() as session:
        await RecordingRepository(session).create("chunk_one.mp4")

    await run_recording_chunk_tick(camera, session_factory, chunk_seconds=1, auto_start=True)

    status = camera.get_recording_status()
    assert status.is_recording is True
    assert status.filename != "chunk_one.mp4"

    async with session_factory() as session:
        rows = await RecordingRepository(session).list_all()
        assert len(rows) == 2
        completed = [r for r in rows if r.filename == "chunk_one.mp4"][0]
        assert completed.status.value == "completed"


async def test_does_not_rotate_before_chunk_duration_elapses(session_factory):
    camera = FakeCamera()
    camera.start_recording("chunk_one.mp4", output_dir=None)  # type: ignore[arg-type]

    async with session_factory() as session:
        await RecordingRepository(session).create("chunk_one.mp4")

    await run_recording_chunk_tick(camera, session_factory, chunk_seconds=3600, auto_start=True)

    status = camera.get_recording_status()
    assert status.filename == "chunk_one.mp4"

    async with session_factory() as session:
        rows = await RecordingRepository(session).list_all()
        assert len(rows) == 1
