# Copilot / AI assistant instructions for cat_sentinel

This is a monorepo of 4 independent services (`camera`, `cat-sentinel`, `hub`, `hub_frontend`).
Each has its own dependency manager (Poetry for the three FastAPI services, npm for the Next.js
frontend) and its own `.env`. Don't assume a shared virtualenv or node_modules across services.

## Conventions to follow in the three FastAPI services

- Domain-per-package layout: every resource gets `router.py` + `schemas.py` + `models.py` +
  `service.py` + `repository.py` under `app/<domain>/`. See
  [`docs/adr/0001-layered-fastapi-architecture.md`](../docs/adr/0001-layered-fastapi-architecture.md).
- Routers stay thin -- call into `service.py`, never touch SQLAlchemy directly.
- Repositories translate SQLAlchemy exceptions (`IntegrityError`, etc.) into domain exceptions
  from `app/core/exceptions.py` before they leave the repository layer.
- Decorate service classes with `@log_errors` (or a single method with `@log_call`) --
  `app/core/decorators.py` -- except methods on a hot path (per-frame/per-tick code), which stay
  undecorated with a comment explaining why.
- New domain exception -> define the class + `@exception_handler(...)`-decorated handler
  together in `app/core/exceptions.py`. Never hand-wire `app.add_exception_handler` in
  `main.py`.
- Alembic migrations are generated (`alembic revision --autogenerate`), never hand-written, and
  always reviewed before applying.
- `camera` does not import any computer-vision/ML library -- see
  [`docs/adr/0002-camera-api-scope-boundary.md`](../docs/adr/0002-camera-api-scope-boundary.md).

## Ports (dev)

`camera=9000`, `cat-sentinel=9001`, `hub=9002`, `hub_frontend=3000`. Set by
[`tools/dev.sh`](../tools/dev.sh), overridable via `CAMERA_PORT`/`CAT_SENTINEL_PORT`/`HUB_PORT`/
`FRONTEND_PORT` env vars.

## Hardware caveat

The target camera is a TP-Link Tapo C200. PTZ is open-loop (no real position feedback from the
camera), so angles are estimated locally and drift -- see `camera/app/ptz/service.py`.

<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->
