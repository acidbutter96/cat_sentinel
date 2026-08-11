from __future__ import annotations

from datetime import UTC

from app.recordings.repository import RecordingRepository
from app.recordings.service import RecordingService


async def test_recordings_list_empty(client):
    response = await client.get("/recordings")
    assert response.status_code == 200
    assert response.json() == []


async def test_recordings_created_via_camera_start_appear_in_list(client):
    await client.post("/recording/start")
    await client.post("/recording/stop")

    response = await client.get("/recordings")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "completed"


async def test_download_missing_recording_returns_404(client):
    response = await client.get("/recordings/does-not-exist.mp4")
    assert response.status_code == 404


async def test_reconciliation_marks_missing_files(db_session, tmp_path, monkeypatch):
    from app.settings.config import settings

    monkeypatch.setattr(settings, "recordings_dir", str(tmp_path))

    repository = RecordingRepository(db_session)
    service = RecordingService(repository)

    recording = await repository.create("ghost.mp4")
    assert recording.status.value == "recording"

    # No file was ever written to tmp_path for "ghost.mp4" -> reconciliation
    # should flip it to MISSING.
    await service.reconcile()

    refreshed = await repository.get_by_filename("ghost.mp4")
    assert refreshed.status.value == "missing"


async def test_reconciliation_updates_file_size_for_existing_completed_file(
    db_session, tmp_path, monkeypatch
):
    from datetime import datetime

    from app.settings.config import settings

    monkeypatch.setattr(settings, "recordings_dir", str(tmp_path))

    repository = RecordingRepository(db_session)
    service = RecordingService(repository)

    recording = await repository.create("real.mp4")
    path = tmp_path / "real.mp4"
    path.write_bytes(b"0" * 1234)
    await repository.mark_completed(recording, datetime.now(UTC), 5.0, file_size_bytes=1)

    await service.reconcile()

    refreshed = await repository.get_by_filename("real.mp4")
    assert refreshed.file_size_bytes == 1234
