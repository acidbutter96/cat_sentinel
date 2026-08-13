import httpx
import pytest

from app.core.dependencies import get_cat_sentinel_control_client
from app.main import app


@pytest.fixture
async def snapshot_upstream():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/snapshots"
        assert request.url.params["path"] == "snapshots/default/cat-1/photo.jpg"
        return httpx.Response(200, content=b"jpeg", headers={"content-type": "image/jpeg"})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://cat-sentinel.test"
    )

    async def override():
        yield client

    app.dependency_overrides[get_cat_sentinel_control_client] = override
    yield
    app.dependency_overrides.clear()
    await client.aclose()


async def test_snapshot_proxy_returns_image(client, snapshot_upstream):
    response = await client.get(
        "/snapshots", params={"path": "snapshots/default/cat-1/photo.jpg"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"jpeg"
