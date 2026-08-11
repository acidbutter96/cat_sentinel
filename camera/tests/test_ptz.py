from __future__ import annotations


async def test_move_updates_estimated_position(client, fake_ptz_controller):
    response = await client.post("/ptz/move", json={"pan": 45.0, "tilt": -10.0})
    assert response.status_code == 200
    assert response.json() == {"pan": 45.0, "tilt": -10.0}
    assert fake_ptz_controller.moves == [(45.0, -10.0)]


async def test_nudge_valid_direction(client, fake_ptz_controller):
    response = await client.post("/ptz/nudge", json={"direction": 90})
    assert response.status_code == 200
    assert fake_ptz_controller.nudges == [90]


async def test_nudge_rejects_out_of_range_direction(client):
    response = await client.post("/ptz/nudge", json={"direction": 360})
    assert response.status_code == 422


async def test_calibrate_resets_position(client, fake_ptz_controller):
    await client.post("/ptz/move", json={"pan": 30.0, "tilt": 5.0})

    response = await client.post("/ptz/calibrate")
    assert response.status_code == 200
    assert response.json() == {"calibrated": True, "pan": 0.0, "tilt": 0.0}
    assert fake_ptz_controller.calibrations == 1


async def test_status_reports_local_estimate(client):
    await client.post("/ptz/move", json={"pan": 12.0, "tilt": 3.0})

    response = await client.get("/ptz/status")
    assert response.status_code == 200
    assert response.json() == {"pan": 12.0, "tilt": 3.0}
