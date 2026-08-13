from app.cats.repository import CatRepository
from app.cats.service import CatService


async def test_list_cats_empty(client):
    response = await client.get("/detected-cats/")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_or_create_cat_then_read_and_patch(client, db_session):
    service = CatService(CatRepository(db_session))
    cat = await service.get_or_create_for_track("cam-1", track_id=7)
    assert cat.label == "cat #7"
    assert cat.is_active is True

    response = await client.get(f"/detected-cats/{cat.id}")
    assert response.status_code == 200
    assert response.json()["label"] == "cat #7"

    patched = await client.patch(f"/detected-cats/{cat.id}", json={"label": "Whiskers"})
    assert patched.status_code == 200
    assert patched.json()["label"] == "Whiskers"


async def test_patch_cat_retire(client, db_session):
    service = CatService(CatRepository(db_session))
    cat = await service.get_or_create_for_track("cam-1", track_id=3)

    patched = await client.patch(f"/detected-cats/{cat.id}", json={"is_active": False})
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False


async def test_get_missing_cat_returns_404(client):
    response = await client.get("/detected-cats/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_get_or_create_is_idempotent(db_session):
    service = CatService(CatRepository(db_session))
    first = await service.get_or_create_for_track("cam-1", track_id=1)
    second = await service.get_or_create_for_track("cam-1", track_id=1)
    assert first.id == second.id


async def test_identify_or_create_reuses_cat_for_similar_embedding_on_new_track_id(db_session):
    """Regression test for the "persistent ID" fix: a cat re-entering frame
    (or the pipeline restarting) gets assigned a brand new track_id, but
    identify_or_create must still resolve it to the SAME Cat.id when the
    appearance embedding matches closely enough -- this is what makes the
    identity survive a track_id reset instead of spawning a duplicate cat.
    """
    service = CatService(CatRepository(db_session))
    embedding = [1.0, 0.0, 0.0, 0.0]

    first = await service.identify_or_create("cam-1", track_id=1, embedding=embedding)
    # A different track_id (as if the tracker lost and reacquired the cat,
    # or the process restarted) but a near-identical embedding.
    second = await service.identify_or_create("cam-1", track_id=99, embedding=[0.99, 0.01, 0.0, 0.0])

    assert first.id == second.id
    assert second.track_id == 99  # last-observed track_id is updated...
    cats = await CatRepository(db_session).list()
    assert len(cats) == 1  # ...but no duplicate Cat row was created


async def test_identify_or_create_creates_new_cat_for_dissimilar_embedding(db_session):
    service = CatService(CatRepository(db_session))
    first = await service.identify_or_create("cam-1", track_id=1, embedding=[1.0, 0.0, 0.0, 0.0])
    second = await service.identify_or_create("cam-1", track_id=2, embedding=[0.0, 0.0, 0.0, 1.0])

    assert first.id != second.id
    cats = await CatRepository(db_session).list()
    assert len(cats) == 2


async def test_identify_or_create_falls_back_to_track_id_without_embedding(db_session):
    service = CatService(CatRepository(db_session))
    cat = await service.identify_or_create("cam-1", track_id=5, embedding=None)
    assert cat.track_id == 5
    assert cat.embedding is None


async def test_touch_updates_embedding_without_changing_identity(db_session):
    service = CatService(CatRepository(db_session))
    cat = await service.identify_or_create("cam-1", track_id=1, embedding=[1.0, 0.0])
    touched = await service.touch(cat.id, embedding=[0.0, 1.0])
    assert touched.id == cat.id
    assert touched.embedding_samples == 2
