# cat-sentinel

Detects and tracks cats via a camera feed and alerts when a cat enters a
"danger zone" polygon (e.g. next to a pet rat terrarium). Standalone FastAPI
service, v0.1.0, no auth (trusted internal network).

## Running

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/docs`.

## Configuration

See `app/settings/config.py`. Key environment variables:

- `DATABASE_URL` — SQLAlchemy async URL (default: local SQLite)
- `CAMERA_STREAM_URL` — MJPEG stream URL of the upstream camera service
- `ALERT_WEBHOOK_URL` — outbound webhook URL fired on danger-zone entry
- `ALERT_COOLDOWN_SECONDS` — per cat+zone cooldown between repeated alerts
- `YOLO_MODEL_PATH` — path/name of the YOLOv8 weights file
- `YOLO_CONFIDENCE_THRESHOLD` — minimum detection confidence
- `CENTROID_MAX_DISTANCE` — max pixel distance for centroid-tracker matching
- `CENTROID_MAX_AGE_FRAMES` — frames a track can go unseen before it's dropped
- `LOG_LEVEL` — root log level

## Tests

```bash
poetry run pytest
```
