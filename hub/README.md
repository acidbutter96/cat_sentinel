# hub

Central FastAPI aggregator that sits in front of two upstream services (`cat-sentinel` and
`camera`) and exposes a simplified surface for the Next.js frontend. `hub` has no database of
its own — it is a thin proxy/aggregator.

## Endpoints

- `GET /trackers` — latest bounding box per actively-tracked cat, read through to upstream
  `cat-sentinel`'s `/cats/` and `/detections/` endpoints.
- `GET /stream/annotated` — proxies the MJPEG annotated stream from upstream `cat-sentinel`'s
  `/stream/annotated`, byte-for-byte, as a streaming response.

## Running

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Configuration

See `app/settings/config.py`. Key env vars:

- `CAT_SENTINEL_BASE_URL` (default `http://localhost:9001`)
- `CAMERA_BASE_URL` (default `http://localhost:9000`)
- `HUB_PORT` (default `8000`)
- `LOG_LEVEL` (default `INFO`)

## Testing

```bash
poetry run pytest
```
