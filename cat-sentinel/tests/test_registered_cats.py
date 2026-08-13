import cv2
import numpy as np

from app.cats.repository import CatRepository
from app.cats.service import CatService
from app.registered_cats.repository import RegisteredCatRepository
from app.registered_cats.schemas import RegisteredCatCreate
from app.registered_cats.service import RegisteredCatService


async def test_register_cat_with_profile_data(client):
    response = await client.post(
        "/cats/",
        json={
            "name": "Luna",
            "birth_date": "2022-04-12",
            "sex": "female",
            "description": "Black cat with a white paw.",
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Luna"
    assert response.json()["sex"] == "female"
    assert response.json()["birth_date"] == "2022-04-12"


async def test_registered_cat_can_link_to_detected_identity(client, db_session):
    detected = await CatService(CatRepository(db_session)).get_or_create_for_track("cam-1", 7)
    response = await client.post(
        "/cats/", json={"name": "Luna", "detected_cat_id": str(detected.id)}
    )
    assert response.status_code == 201
    assert response.json()["detected_cat_id"] == str(detected.id)


async def test_update_registered_cat(client):
    created = await client.post("/cats/", json={"name": "Luna"})
    response = await client.patch(
        f"/cats/{created.json()['id']}",
        json={"name": "Luna Silva", "description": "Rescued in 2024."},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Luna Silva"
    assert response.json()["description"] == "Rescued in 2024."


async def test_upload_reference_image_stores_profile_photo(client, tmp_path, monkeypatch):
    from app.settings.config import settings

    monkeypatch.setattr(settings, "registered_cat_image_dir", str(tmp_path))
    created = await client.post("/cats/", json={"name": "Luna"})
    ok, encoded = cv2.imencode(".jpg", np.full((24, 24, 3), 120, dtype=np.uint8))
    assert ok

    uploaded = await client.post(
        f"/cats/{created.json()['id']}/images",
        content=encoded.tobytes(),
        headers={"content-type": "image/jpeg"},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["photo_path"] is not None

    image = await client.get(f"/cats/{created.json()['id']}/photo")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"


async def test_reference_embedding_links_new_detected_cat(db_session):
    registered_service = RegisteredCatService(RegisteredCatRepository(db_session))
    registered = await registered_service.create(RegisteredCatCreate(name="Luna"))
    await registered_service.add_reference_image(
        registered.id, "registered_cat_images/luna.jpg", [1.0, 0.0, 0.0]
    )

    matched = await registered_service.find_best_match([0.99, 0.01, 0.0])
    assert matched is not None
    assert matched.id == registered.id

    detected = await CatService(CatRepository(db_session)).identify_or_create(
        "cam-1",
        track_id=1,
        embedding=[0.99, 0.01, 0.0],
        registered_cat_id=matched.id,
        registered_cat_name=matched.name,
    )
    assert detected.registered_cat_id == registered.id
    assert detected.label == "Luna"
