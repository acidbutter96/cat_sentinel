# cat_sentinel

A system that watches a room via camera and alerts when a **cat** enters a
"danger zone" (e.g. the table next to a pet's terrarium). Four independent services,
each its own Poetry/yarn project, orchestrated locally by [`tools/dev.sh`](tools/dev.sh).

```
cat_sentinel/
├── camera/          # RTSP -> HTTP bridge + PTZ control (port 9000 in dev)
├── cat-sentinel/     # cat detection/tracking via YOLOv8 (port 9001 in dev)
├── hub/              # central aggregator API for the frontend (port 9002 in dev)
├── hub_frontend/      # Next.js dashboard, consumes hub (port 3000 in dev, 9003 in docker)
├── docker-compose.yml  # Postgres (two databases) + camera/cat-sentinel/hub/frontend containers
├── docs/               # ADRs
└── tools/dev.sh         # brings up Postgres + all four services locally
```

Hardware target: **TP-Link Tapo C200**. RTSP on port 554, PTZ control via `pytapo`. PTZ is
open-loop (no real position feedback), so angles are estimated locally and drift -- see
[`camera/app/ptz/service.py`](camera/app/ptz/service.py) and `POST /ptz/calibrate` to resync.

## Architecture

```mermaid
flowchart TB
    subgraph external["External actors"]
        cam["Tapo C200<br/>(RTSP :554)"]
        user["Browser<br/>(dashboard user)"]
    end

    subgraph camerasvc["camera service :9000"]
        camrouter["routers<br/>camera / ptz / events / webhooks / recordings"]
        camcore["core<br/>decorators, exceptions, DI"]
        rtsp["RTSPCamera<br/>background decode thread"]
    end

    subgraph catsvc["cat-sentinel service :9001"]
        catrouter["routers<br/>zones / cats / detections / alerts / activities / stream"]
        catcore["core<br/>decorators, exceptions, DI"]
        pipeline["DetectionPipeline<br/>YOLOv8 + centroid tracker"]
    end

    subgraph hubsvc["hub service :9002"]
        hubrouter["routers<br/>trackers / stream proxy"]
    end

    subgraph fe["hub_frontend :3000"]
        feroutes["/api/trackers, /api/stream"]
        fepage["/live page"]
    end

    pg[("Postgres<br/>cat_sentinel db + camera db")]

    cam -->|RTSP| rtsp
    rtsp --> camrouter
    camrouter -->|snapshot/video| pipeline
    pipeline -->|POST /events/trigger| camrouter
    pipeline --> catrouter
    catrouter -->|alert webhook| camrouter
    camrouter --> pg
    catrouter --> pg

    hubrouter -->|GET /trackers, /stream/annotated| catrouter
    feroutes --> hubrouter
    fepage --> feroutes
    user --> fepage

    classDef ext fill:#94a3b8,stroke:#475569,color:#0f172a
    classDef cam fill:#38bdf8,stroke:#0284c7,color:#0f172a
    classDef cat fill:#4ade80,stroke:#16a34a,color:#0f172a
    classDef hub fill:#facc15,stroke:#ca8a04,color:#0f172a
    classDef front fill:#c084fc,stroke:#9333ea,color:#0f172a
    classDef store fill:#f97316,stroke:#c2410c,color:#0f172a

    class cam,user ext
    class camrouter,camcore,rtsp cam
    class catrouter,catcore,pipeline cat
    class hubrouter hub
    class feroutes,fepage front
    class pg store
```

## Stream pipeline (camera service)

```mermaid
flowchart LR
    a["RTSP<br/>source"] --> b["RTSPCamera<br/>background decode thread"]
    b --> c["decode loop"]
    c --> d["shared frame buffer"]
    d --> e["GET /video<br/>MJPEG multipart"]
    d --> f["GET /snapshot<br/>latest JPEG"]
    d --> g["recording writer<br/>(reuses buffer, no 2nd RTSP conn)"]
    g --> h[("recordings table<br/>Postgres")]

    classDef stage fill:#38bdf8,stroke:#0284c7,color:#0f172a
    classDef store fill:#f97316,stroke:#c2410c,color:#0f172a
    class a,b,c,d,e,f,g stage
    class h store
```

## Detection & alert sequence

```mermaid
sequenceDiagram
    participant Pipeline as DetectionPipeline (cat-sentinel)
    participant Vision as YoloCatDetector + CentroidTracker
    participant DB as Postgres
    participant Camera as camera service
    participant Webhook as subscriber webhook

    Pipeline->>Camera: GET /video (MJPEG frames)
    loop every frame
        Pipeline->>Vision: detect + track cats
        Vision-->>Pipeline: bbox, track_id, centroid
        Pipeline->>Pipeline: point-in-polygon vs active zones
        Pipeline->>DB: persist Detection row
        alt cat entered danger zone (cooldown elapsed)
            Pipeline->>DB: persist Alert row
            Pipeline->>Camera: POST /events/trigger
            Camera->>Camera: map event_type -> command via dispatcher
            Camera->>Webhook: fan-out POST (best-effort, 3s timeout)
        end
    end
```

## Local dev

```bash
cp .env.example .env
./tools/dev.sh
```

This brings up Postgres (two databases: `cat_sentinel`, `camera`) and all four services.
See each service's own README for its `.env` and `poetry install` / `yarn install` steps.

## Docker

All four services -- `camera`, `cat-sentinel`, `hub`, and `hub_frontend` -- have a
`Dockerfile` and are wired into [`docker-compose.yml`](docker-compose.yml) alongside
Postgres. `hub_frontend`'s container runs `yarn dev` with the source mounted as a volume,
so it hot-reloads like the local flow.

```bash
cp .env.example .env
docker compose up -d --build
docker compose run --rm cat-sentinel alembic upgrade head
docker compose run --rm camera alembic upgrade head
```

Notes:
- Each service's own `.env` (`camera/.env`, `cat-sentinel/.env`) is loaded via `env_file`;
  `DATABASE_URL` and cross-service URLs are overridden in `docker-compose.yml` to use the
  Postgres/service container names instead of `localhost`.
- Migrations aren't run automatically on container start -- run them once per fresh
  Postgres volume as shown above.
- `camera`'s startup blocks on a PTZ auth probe against the real Tapo camera
  (`CAMERA_HOST`/`TAPO_CONTROL_USER`/`TAPO_CONTROL_PASSWORD` in `camera/.env`) -- it will
  crash-loop under `docker compose` if that camera isn't reachable from the container's
  network, same as running it locally.
- `hub_frontend` is published on `9003` by default (override with `FRONTEND_PORT`), not
  `3000` -- avoids clashing with a locally-run `yarn dev` on the same machine.

## Docs

- [`docs/adr/0001-layered-fastapi-architecture.md`](docs/adr/0001-layered-fastapi-architecture.md)
- [`docs/adr/0002-camera-api-scope-boundary.md`](docs/adr/0002-camera-api-scope-boundary.md)
