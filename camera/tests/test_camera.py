from __future__ import annotations


async def test_status(client):
    response = await client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["transport"] == "tcp"


async def test_reset(client, fake_camera):
    response = await client.post("/reset")
    assert response.status_code == 200
    assert response.json() == {"reset": True}
    assert fake_camera._reset_called == 1


async def test_snapshot_returns_jpeg(client):
    response = await client.get("/snapshot")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


async def test_snapshot_503_when_no_frame(client, fake_camera):
    fake_camera._frame = None
    response = await client.get("/snapshot")
    assert response.status_code == 503


async def test_recording_start_stop_status(client):
    status_before = await client.get("/recording/status")
    assert status_before.json()["is_recording"] is False

    start = await client.post("/recording/start")
    assert start.status_code == 200
    assert start.json()["started"] is True
    filename = start.json()["filename"]

    status_during = await client.get("/recording/status")
    assert status_during.json()["is_recording"] is True
    assert status_during.json()["filename"] == filename

    stop = await client.post("/recording/stop")
    assert stop.status_code == 200
    assert stop.json()["stopped"] is True
    assert stop.json()["filename"] == filename

    status_after = await client.get("/recording/status")
    assert status_after.json()["is_recording"] is False


async def test_recording_start_twice_returns_409(client):
    first = await client.post("/recording/start")
    assert first.status_code == 200

    second = await client.post("/recording/start")
    assert second.status_code == 409

    await client.post("/recording/stop")
