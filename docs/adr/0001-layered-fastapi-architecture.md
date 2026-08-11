# 0001 - Layered FastAPI architecture (domain-per-package)

## Status
Accepted

## Context
Three of the four services in this monorepo (`camera`, `cat-sentinel`, `hub`) are FastAPI
applications. FastAPI itself is unopinionated about project layout, which invites drift: every
new contributor (or every new session with an AI coding assistant) tends to invent its own
convention for where a router, a schema, or a DB query belongs. That drift compounds over a
project's lifetime into inconsistent, hard-to-navigate code.

## Decision
Every FastAPI service in this monorepo follows the same domain-per-package layout:

```
app/<domain>/
├── router.py       # thin: parses via Pydantic, calls service, returns schema
├── schemas.py       # Create / Update (all fields optional) / Read (from_attributes=True)
├── models.py         # SQLAlchemy 2.0, Mapped[...] / mapped_column
├── service.py         # business logic, decorated with @log_errors
└── repository.py       # DB queries only, translates SQLAlchemy failures into domain exceptions
```

`settings/` (how the app is configured and observed as a whole -- env config, logging setup,
global middleware) is kept separate from `core/` (framework machinery domain code reaches for
directly -- DI providers, decorators, the exception registry). `core/` never imports from a
domain package; only the reverse.

Cross-cutting concerns (auth, pagination, feature flags) are dependencies, declared in each
route's signature, not decorators bolted onto every function and not global middleware unless
the concern truly applies to every request (request-id/timing logging is the deliberate
exception -- see `settings/middleware.py` in each service).

Uniqueness constraints are enforced at the DB level (`unique=True`) as the source of truth,
with the repository layer catching `IntegrityError` and translating it into a domain
`ConflictError` (409) -- never a "SELECT before INSERT" existence check as the only guard,
since that's racy under concurrent writes.

`camera` deviates slightly: it organizes top-level folders by *capability* ("screaming
architecture" -- `camera/`, `events/`, `webhooks/`, `recordings/`) rather than a flat list of
REST resources, because its domains aren't uniformly REST resources (the `camera/` folder is
mostly RTSP-bridge machinery, not a CRUD domain). Internally, each folder that does own
persistence still follows the same five-file shape.

## Consequences
- Adding a new resource is a mechanical five-file addition, not a judgment call.
- "Where does X live for the `zones` domain" always has the same answer shape across all three
  backends.
- Slight ceremony for very small domains (e.g. a read-only `GET /health`), which is why trivial
  endpoints like that are added directly in `main.py` rather than getting a full package.
