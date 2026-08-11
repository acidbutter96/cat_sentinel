# 0002 - camera service scope boundary: no computer vision/ML

## Status
Accepted

## Context
Early on, it would have been tempting to put cat detection directly into the `camera` service,
since it already holds the decoded frame buffer -- no second network hop needed. But `camera`'s
job is specifically to be a stable bridge between an unreliable, quirky piece of consumer IP
camera hardware (RTSP/HEVC, non-conformant PLAY replies, ONVIF-only control) and a normal HTTP
API. Mixing in YOLO inference would couple that hardware-facing code to a completely different
concern (computer vision) with different scaling, dependency, and failure characteristics
(GPU/CPU-bound inference vs. I/O-bound stream proxying).

## Decision
`camera` moves video and events only. It never imports a CV/ML library and never answers "is
there a cat in this frame" itself. That question is answered by a separate microservice,
`cat-sentinel`, which:

1. Pulls frames from `camera`'s `GET /video` (or `GET /snapshot`) like any other HTTP client --
   no special access to `camera`'s internals.
2. Runs its own detection/tracking pipeline.
3. Posts results back to `camera`'s `POST /events/trigger`, which maps them to camera commands
   (today: logged only, via `LoggingCameraCommandDispatcher`; a real actuator API for
   siren/light/PTZ was never built).

## Consequences
- `camera` can be deployed, scaled, and rebooted independently of whatever ML stack
  `cat-sentinel` uses (YOLOv8 today, could change without touching `camera` at all).
- `camera`'s dependency footprint stays small (RTSP/HEVC decode, HTTP, Postgres) -- no
  `ultralytics`/`torch` anywhere near the hardware-facing service.
- Adds one network hop (`cat-sentinel` -> `camera` -> `cat-sentinel`) per detection cycle,
  which is an accepted cost for the isolation.
- Any future service that wants to react to camera frames (e.g. a second detector) can consume
  `camera`'s `/video`/`/snapshot` the same way `cat-sentinel` does, without `camera` needing to
  know about it.
