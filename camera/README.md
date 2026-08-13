# jortan-camera-api

RTSP-to-HTTP bridge and PTZ control for the TP-Link Tapo C200 IP camera.

This service owns exactly one job: get video, events, and pan/tilt control off a single
camera and onto HTTP, reliably. It does **not** do any computer vision or ML — object/animal
detection lives in a separate microservice (`cat-sentinel`) that polls this service's
`/video` or `/snapshot` endpoints and posts its findings back to `POST /events/trigger`. See
`app/events/router.py` for the full boundary note.

## Domains (screaming architecture)

- `app/camera/` — the RTSP bridge itself: `RTSPCamera` background decode thread, live MJPEG
  stream, snapshot, status, reset, and recording start/stop/status.
- `app/ptz/` — pan/tilt control via `pytapo`. **Open-loop, not absolute**: the Tapo C200
  reports no real position feedback, so angles are estimated locally and drift — see the
  caveat in `app/ptz/service.py` and use `POST /ptz/calibrate` to resync.
- `app/recordings/` — DB-backed recording metadata (Postgres via Alembic) plus a background
  reconciliation scheduler.
- `app/events/` — ingests detection triggers from `cat-sentinel` and dispatches camera
  commands. `ptz_move` / `ptz_nudge` / `ptz_calibrate` map to the real PTZ controller;
  everything else (siren/light — the C200 has neither built in) only logs.
- `app/webhooks/` — outbound fan-out of every event to subscriber URLs.
- `app/settings/` — config, logging, middleware.
- `app/core/` — cross-domain DI, decorators, self-registering exception handlers.
- `app/db/` — SQLAlchemy async engine/session/base.

## Camera setup (Tapo C200)

1. In the Tapo app: **Settings > Advanced Settings > Camera Account** — create/note the
   local RTSP/ONVIF account. Use it for `CAMERA_RTSP_USER` / `CAMERA_RTSP_PASSWORD`.
2. Use your TP-Link cloud account (or the same local account, depending on firmware) for
   `TAPO_CONTROL_USER` / `TAPO_CONTROL_PASSWORD` — this is what `pytapo` uses for PTZ.
3. RTSP paths: `/stream1` (HD/main) or `/stream2` (SD/sub, lower latency).

## Running locally

```bash
poetry install
cp .env.example .env  # edit camera credentials
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Open `http://localhost:8000/` for the live viewer, `http://localhost:8000/docs` for the API
(including `POST /ptz/move`, `POST /ptz/nudge`, `POST /ptz/calibrate`, `GET /ptz/status`).

Set `LIVE_JPEG_QUALITY` and `MJPEG_FRAME_INTERVAL_SECONDS` to control only the
live MJPEG feed. RTSP recordings retain their source quality.

## Testing

```bash
poetry run pytest
```
