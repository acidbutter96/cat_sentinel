# cat-sentinell — 2026-08-12

- `cat-sentinel` now runs `alembic upgrade head` before Uvicorn in Docker Compose.
- Applied revision `b7c3d9e1f2a4` to the running PostgreSQL database, adding the
  cat re-identification columns and alert fields required by the current code.
- Fixed the hub startup assertion on the 204 zone-delete proxy route; both the
  hub stream and frontend stream proxy now return continuous MJPEG responses.
- Added one padded cat-crop JPEG per new camera entry, stored under the bound
  `cat-sentinel/snapshots` directory and referenced by `detections.snapshot_path`.
- Added migration `c8d4e5f6a7b8` to add the snapshot reference and widen
  `activities.kind` for `ENTERED_FRAME`.
- Added safe snapshot serving through cat-sentinel, hub, and the frontend
  same-origin API; live tracker cards now show the cat image and current box.
- Hub tracker aggregation now fetches up to 200 records, resolves cat labels,
  and hides detections older than eight seconds from the live view.
