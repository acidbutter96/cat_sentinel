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
- `SNAPSHOT_DIR` — local directory for cat snapshot crops (default: `snapshots`)
- `REGISTERED_CAT_IMAGE_DIR` — local directory for registered-cat reference images

When a cat enters the camera view, the detector saves one cropped JPEG under
`SNAPSHOT_DIR/<camera>/<cat>/` and stores its relative path in
`detections.snapshot_path`. The Docker Compose volume maps this directory to
`./cat-sentinel/snapshots` on the host.

The same new-track `detections` record also stores the complete source frame
(`frame_path`), exact UTC capture timestamp, tracker `track_id`, and bounding
box. Those fields are the durable selection record used to reconstruct a
tracking visualization.

## Cat data

- `detected_cats` is owned by the detection pipeline and stores anonymous,
  appearance-based identities, tracks, and embeddings. Use `GET /detected-cats/`
  to inspect them.
- `registered_cats` is the manual registry. Use `POST /cats/` with `name`,
  optional `birth_date`, `sex` (`female`, `male`, or `unknown`), `description`,
  and an optional `detected_cat_id` to link the profile to a detected identity.
  Upload one or more JPEG, PNG, or WebP reference images with
  `POST /cats/{cat_id}/images`; the most recent image is shown as the profile
  photo at `GET /cats/{cat_id}/photo`.
- On a new camera track, the detector compares its appearance embedding with all
  registered reference images. A match links `detected_cats.registered_cat_id`
  while `detections` retains the new-track snapshot used by the live tracker.

## Tests

```bash
poetry run pytest
```
