from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.dependencies import (
    build_cat_sentinel_control_client,
    build_cat_sentinel_stream_client,
)
from app.core.exceptions import register_exception_handlers
from app.settings.config import settings
from app.settings.logging_config import setup_logging
from app.settings.middleware import register_middleware
from app.stream.router import router as stream_router
from app.trackers.router import router as trackers_router

setup_logging(settings.log_level, settings.log_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Two distinct clients on purpose -- see core/dependencies.py docstring.
    app.state.cat_sentinel_control_client = build_cat_sentinel_control_client()
    app.state.cat_sentinel_stream_client = build_cat_sentinel_stream_client()
    try:
        yield
    finally:
        await app.state.cat_sentinel_control_client.aclose()
        await app.state.cat_sentinel_stream_client.aclose()


app = FastAPI(title="hub", lifespan=lifespan)
register_middleware(app)
register_exception_handlers(app)
app.include_router(trackers_router)
app.include_router(stream_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
