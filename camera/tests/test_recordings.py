from __future__ import annotations

from datetime import UTC

import av
from PIL import Image

from app.camera.service import RTSPCamera
from app.recordings.models import Recording
from app.recordings.repository import RecordingRepository
from app.recordings.service import RecordingService


def test_recording_status_uses_database_enum_values():
    status_type = Recording.__table__.c.status.type
    assert status_type.enums == ["recording", "completed", "failed", "missing"]


def test_recording_is_finalized_as_a_playable_mp4(tmp_path):
    camera = RTSPCamera("rtsp://unused")
    camera._last_frame_size = (64, 48)
    path = tmp_path / "recording.mp4"
    camera.start_recording(path.name, tmp_path)
    camera._process_frame(av.VideoFrame.from_image(Image.new("RGB", (64, 48), "red")))
    camera._process_frame(av.VideoFrame.from_image(Image.new("RGB", (64, 48), "blue")))
    camera.stop_recording()

    with av.open(str(path)) as container:
        assert container.streams.video[0].codec_context.name == "mpeg4"
        decoded = next(container.decode(video=0))
        assert (decoded.width, decoded.height) == (64, 48)


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
