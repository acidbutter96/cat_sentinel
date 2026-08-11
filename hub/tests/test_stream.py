import httpx
import pytest

from app.core.dependencies import get_cat_sentinel_stream_client
from app.main import app
from app.stream.service import StreamService

MJPEG_BODY = b"--frame\r\nContent-Type: image/jpeg\r\n\r\nFAKEJPEGBYTES\r\n--frame\r\n"


@pytest.fixture
async def mock_stream_client():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=MJPEG_BODY,
            headers={"content-type": "multipart/x-mixed-replace; boundary=frame"},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://cat-sentinel.test")

    async def _override():
        yield client

    app.dependency_overrides[get_cat_sentinel_stream_client] = _override
    yield client
    app.dependency_overrides.clear()
    await client.aclose()


async def test_stream_annotated_proxies_bytes_and_content_type(client, mock_stream_client):
    async with client.stream("GET", "/stream/annotated") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
        body = b""
        async for chunk in response.aiter_bytes():
            body += chunk
    assert body == MJPEG_BODY


@pytest.fixture
async def unreachable_stream_client():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://cat-sentinel.test")

    async def _override():
        yield client

    app.dependency_overrides[get_cat_sentinel_stream_client] = _override
    yield client
    app.dependency_overrides.clear()
    await client.aclose()


async def test_stream_annotated_upstream_down_returns_502(client, unreachable_stream_client):
    response = await client.get("/stream/annotated")
    assert response.status_code == 502


# --- body_iterator-level tests (per skill guidance for streaming responses) --


class _FakeUpstreamResponse:
    """Fakes just enough of httpx.Response to drive iter_annotated_stream
    directly, so we can assert the upstream connection is closed when the
    downstream client disconnects early (GeneratorExit thrown mid-iteration)."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks
        self.closed = False

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk

    async def aclose(self):
        self.closed = True


async def test_iter_annotated_stream_yields_chunks_unchanged():
    service = StreamService(stream_client=httpx.AsyncClient())
    fake_response = _FakeUpstreamResponse([b"a", b"b", b"c"])

    collected = []
    async for chunk in service.iter_annotated_stream(fake_response):
        collected.append(chunk)

    assert collected == [b"a", b"b", b"c"]
    assert fake_response.closed is True


async def test_iter_annotated_stream_closes_upstream_on_early_disconnect():
    service = StreamService(stream_client=httpx.AsyncClient())
    fake_response = _FakeUpstreamResponse([b"a", b"b", b"c"])

    gen = service.iter_annotated_stream(fake_response)
    first = await gen.__anext__()
    assert first == b"a"

    # Simulate the downstream client disconnecting mid-stream: Starlette
    # throws GeneratorExit into the body_iterator generator.
    await gen.aclose()

    assert fake_response.closed is True
