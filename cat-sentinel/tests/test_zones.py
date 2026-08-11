import math

from tests.factories import make_zone_payload


async def test_create_zone(client):
    response = await client.post("/zones/", json=make_zone_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "terrarium-perimeter"
    assert body["camera_id"] == "cam-1"
    assert len(body["points"]) == 3


async def test_get_zone(client):
    created = (await client.post("/zones/", json=make_zone_payload())).json()
    response = await client.get(f"/zones/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_missing_zone_returns_404(client):
    response = await client.get("/zones/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_list_zones(client):
    await client.post("/zones/", json=make_zone_payload(name="zone-a"))
    await client.post("/zones/", json=make_zone_payload(name="zone-b"))
    response = await client.get("/zones/")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_patch_zone(client):
    created = (await client.post("/zones/", json=make_zone_payload())).json()
    response = await client.patch(f"/zones/{created['id']}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_delete_zone(client):
    created = (await client.post("/zones/", json=make_zone_payload())).json()
    response = await client.delete(f"/zones/{created['id']}")
    assert response.status_code == 204
    follow_up = await client.get(f"/zones/{created['id']}")
    assert follow_up.status_code == 404


async def test_zone_requires_minimum_three_points(client):
    payload = make_zone_payload(points=[{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}])
    response = await client.post("/zones/", json=payload)
    assert response.status_code == 422


async def test_zone_caps_at_two_hundred_points(client):
    points = [{"x": float(i), "y": float(i)} for i in range(201)]
    payload = make_zone_payload(points=points)
    response = await client.post("/zones/", json=payload)
    assert response.status_code == 422


async def test_zone_rejects_infinite_coordinates(client):
    payload = make_zone_payload(
        points=[{"x": math.inf, "y": 0.0}, {"x": 1.0, "y": 1.0}, {"x": 2.0, "y": 2.0}]
    )
    response = await client.post("/zones/", json=payload)
    assert response.status_code == 422
    # The default validation-error handler must not crash trying to
    # JSON-serialize the echoed inf/nan value -- confirm we get a real body.
    body = response.json()
    assert "detail" in body


async def test_zone_rejects_nan_coordinates(client):
    payload = make_zone_payload(
        points=[{"x": math.nan, "y": 0.0}, {"x": 1.0, "y": 1.0}, {"x": 2.0, "y": 2.0}]
    )
    response = await client.post("/zones/", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


async def test_create_zone_duplicate_name_returns_409(client):
    payload = make_zone_payload()
    first = await client.post("/zones/", json=payload)
    assert first.status_code == 201

    second = await client.post("/zones/", json=payload)
    assert second.status_code == 409


async def test_update_zone_name_collision_returns_409_without_mutating_original(client):
    a = (await client.post("/zones/", json=make_zone_payload(name="north-lot"))).json()
    b = (await client.post("/zones/", json=make_zone_payload(name="south-lot"))).json()

    response = await client.patch(f"/zones/{b['id']}", json={"name": "north-lot"})
    assert response.status_code == 409

    unchanged = await client.get(f"/zones/{a['id']}")
    assert unchanged.json()["name"] == "north-lot"


async def test_zone_name_unique_per_camera_only(client):
    # Same name, different camera_id -- should NOT conflict.
    payload_cam1 = make_zone_payload(camera_id="cam-1", name="shared-name")
    payload_cam2 = make_zone_payload(camera_id="cam-2", name="shared-name")
    await client.post("/zones/", json=payload_cam1)
    response = await client.post("/zones/", json=payload_cam2)
    assert response.status_code == 201
