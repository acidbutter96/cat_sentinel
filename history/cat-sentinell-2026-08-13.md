# cat-sentinell — 2026-08-13

- Added snapshot image proxying through cat-sentinel, hub, and the frontend.
- Live hub tracker cards now show the cat name, latest snapshot, bounding box,
  confidence, danger-zone state, and detection age.
- Hub tracker reads now fetch up to 200 cats/detections and exclude entries
  older than eight seconds.
- Corrigida a gravação MP4: o enum de status agora persiste os valores lowercase
  esperados pelo PostgreSQL, o timestamp dos frames é definido na taxa de
  gravação, o contêiner é finalizado com segurança e gravações órfãs são
  marcadas como `failed`. Validação: 46 testes, Ruff, `ffprobe` e gravação
  operacional de 21 segundos em MP4 1280x720.
- Reset the `cat_sentinel` schema and rebuilt it at Alembic revision
  `e9f0a1b2c3d4`; the camera database and recording volume were preserved.
- Split anonymous detector identities into `detected_cats` and added the
  human-managed `registered_cats` registry with name, birth date, sex,
  description, and an optional detector identity link.
- Added multiple registered-cat reference-image uploads, stored embeddings, and
  automatic association of a new camera track to the best matching profile.
- Kept the first-entry crop in `detections.snapshot_path` after identity
  association, so the live tracker retains the selected tracking image.
- Reduced live MJPEG to JPEG quality 60 at a 0.1-second frame interval; RTSP
  recordings are unchanged.
- Rerouted the hub live feed directly to the camera `/video` endpoint and
  removed annotated-MJPEG generation and serving from cat-sentinel. The
  detector now contributes only tracking metrics, alerts, and snapshots.
- Fixed the live-feed status overlay for browsers that do not fire `img.load`
  for infinite MJPEG responses, and added a configurable allowed LAN origin
  for Next.js development assets.
- Stored the full entry frame, exact capture time, tracker ID, and selection
  bounding box beside each new-track crop in `detections`.
