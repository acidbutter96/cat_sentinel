import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """ASGI test client -- hub has no DB, so no session fixture is needed.

    The app's lifespan still runs (creating/closing the two upstream httpx
    clients), so tests exercise the same startup/shutdown path as production.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def anyio_backend():
    return "asyncio"


class MockTransport(httpx.AsyncBaseTransport):
    """Minimal reusable mock transport for building fake httpx.AsyncClient
    instances that stand in for the upstream cat-sentinel service in tests.
    """

    def __init__(self, handler):
        self._handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self._handler(request)
