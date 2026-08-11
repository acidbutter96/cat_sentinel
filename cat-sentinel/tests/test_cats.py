from app.cats.repository import CatRepository
from app.cats.service import CatService


async def test_list_cats_empty(client):
    response = await client.get("/cats/")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_or_create_cat_then_read_and_patch(client, db_session):
    service = CatService(CatRepository(db_session))
    cat = await service.get_or_create_for_track("cam-1", track_id=7)
    assert cat.label == "cat #7"
    assert cat.is_active is True

    response = await client.get(f"/cats/{cat.id}")
    assert response.status_code == 200
    assert response.json()["label"] == "cat #7"

    patched = await client.patch(f"/cats/{cat.id}", json={"label": "Whiskers"})
    assert patched.status_code == 200
    assert patched.json()["label"] == "Whiskers"


async def test_patch_cat_retire(client, db_session):
    service = CatService(CatRepository(db_session))
    cat = await service.get_or_create_for_track("cam-1", track_id=3)

    patched = await client.patch(f"/cats/{cat.id}", json={"is_active": False})
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False


async def test_get_missing_cat_returns_404(client):
    response = await client.get("/cats/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_get_or_create_is_idempotent(db_session):
    service = CatService(CatRepository(db_session))
    first = await service.get_or_create_for_track("cam-1", track_id=1)
    second = await service.get_or_create_for_track("cam-1", track_id=1)
    assert first.id == second.id
