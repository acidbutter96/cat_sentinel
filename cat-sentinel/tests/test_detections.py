from app.cats.repository import CatRepository
from app.cats.service import CatService
from app.detections.repository import DetectionRepository
from app.detections.schemas import Centroid, DetectionCreate
from app.detections.service import DetectionService


async def _make_detection(db_session, camera_id: str, track_id: int, in_danger_zone: bool):
    cat_service = CatService(CatRepository(db_session))
    cat = await cat_service.get_or_create_for_track(camera_id, track_id)

    detection_service = DetectionService(DetectionRepository(db_session))
    detection = await detection_service.create(
        DetectionCreate(
            cat_id=cat.id,
            camera_id=camera_id,
            zone_id=None,
            bbox=[0.0, 0.0, 10.0, 10.0],
            centroid=Centroid(x=5.0, y=5.0),
            in_danger_zone=in_danger_zone,
            confidence=0.9,
        )
    )
    return cat, detection


async def test_list_detections_empty(client):
    response = await client.get("/detections/")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_detections_filter_by_cat_id(client, db_session):
    cat_a, _ = await _make_detection(db_session, "cam-1", track_id=1, in_danger_zone=False)
    cat_b, _ = await _make_detection(db_session, "cam-1", track_id=2, in_danger_zone=False)

    response = await client.get("/detections/", params={"cat_id": str(cat_a.id)})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["cat_id"] == str(cat_a.id)
    assert cat_a.id != cat_b.id


async def test_list_detections_filter_by_in_danger_zone(client, db_session):
    await _make_detection(db_session, "cam-1", track_id=1, in_danger_zone=True)
    await _make_detection(db_session, "cam-1", track_id=2, in_danger_zone=False)

    response = await client.get("/detections/", params={"in_danger_zone": "true"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["in_danger_zone"] is True


async def test_list_detections_pagination(client, db_session):
    for i in range(5):
        await _make_detection(db_session, "cam-1", track_id=i, in_danger_zone=False)

    response = await client.get("/detections/", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) == 2
