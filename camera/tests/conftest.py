from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_camera, get_ptz_controller
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from tests.fakes import FakeCamera, FakePTZController

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def fake_camera():
    return FakeCamera()


@pytest.fixture
def fake_ptz_controller():
    return FakePTZController()


@pytest.fixture
async def client(
    db_session: AsyncSession, fake_camera: FakeCamera, fake_ptz_controller: FakePTZController
):
    async def _override_get_db_session():
        yield db_session

    def _override_get_camera():
        return fake_camera

    def _override_get_ptz_controller():
        return fake_ptz_controller

    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_camera] = _override_get_camera
    app.dependency_overrides[get_ptz_controller] = _override_get_ptz_controller

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
