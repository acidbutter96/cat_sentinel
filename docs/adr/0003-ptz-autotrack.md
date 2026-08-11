# 0003 - PTZ auto-tracking: throttled HTTP from cat-sentinel, not a socket

## Status
Proposed

## Context
We want the camera to physically pan/tilt to keep a tracked cat centered in frame, driven off
`cat-sentinel`'s per-frame detections. The open question was transport: should `cat-sentinel`
push pan/tilt targets to `camera` over a persistent socket (WebSocket) for lower latency, or
call `camera`'s existing REST `PTZ` API on a throttle?

Relevant constraints already encoded in the code:

- `camera/app/ptz/service.py`'s `PTZController` is explicitly **open-loop**: the Tapo C200
  exposes no ONVIF absolute positioning or position feedback. `pytapo.moveMotor` is a
  synchronous, `requests`-based call, and the tracked pan/tilt is a local estimate that drifts
  until `calibrate()` is called. Physical motor travel takes on the order of seconds.
- `cat-sentinel`'s detection loop already runs on a fixed interval
  (`detection_frame_interval_seconds = 0.2`, i.e. ~5 fps), and pulls frames from `camera` over
  plain HTTP MJPEG (`RatSentinelStreamClient`).
- Every existing inter-service link in this monorepo is HTTP request/response: `cat-sentinel` →
  `camera` (`POST /events/trigger`, `GET /video`), `hub` → `cat-sentinel` (read-through polling
  in `TrackerService`, no caching), and (presumably) `hub_frontend` → `hub`. Nothing here uses a
  socket today, despite `websockets` being present as a transitive dependency.
- The existing `POST /events/trigger` → command-map → `TapoCameraCommandDispatcher` path
  already knows how to dispatch `ptz_move`, but the command's `params` are a **static** mapping
  configured once via `PUT /events/commands/{event_type}` (see `EventCommandMapService`), not
  derived from the triggering payload. It's built for occasional named alerts
  (`cat_detected`, `intruder_detected`) with a bounded in-memory log, not a continuous stream of
  dynamically-computed pan/tilt values every frame.
- ADR 0002 draws a hard boundary: `camera` never does CV/ML, `cat-sentinel` never talks to
  hardware directly except through `camera`'s HTTP API.

## Decision
Drive PTZ auto-tracking with **throttled HTTP calls from `cat-sentinel` directly to `camera`'s
existing `POST /ptz/move`**, bypassing the `/events/trigger` command-map layer. No socket.

Rationale: the gimbal itself is the bottleneck, not the network. A WebSocket would shave
milliseconds off delivery to a motor that takes seconds to move and has no position feedback to
close the loop tighter anyway. Introducing a persistent, stateful connection also adds a new
failure mode (a dropped socket silently stops tracking) that a plain per-call HTTP request
doesn't have, and it breaks the request/response consistency every other link in this codebase
already follows.

### Implementation sketch

1. **`AutoTrackController`** (new, `cat-sentinel/app/vision/`): pure, no I/O, same style as
   `CentroidTracker` — unit-testable with synthetic bbox/frame-size input. Takes a tracked
   centroid + frame width/height, returns a pan/tilt delta via a proportional controller
   (`error_px / frame_dim * assumed_fov_deg * Kp`).
2. **Deadband**: skip the move if the centroid is already within ~10-15% of frame center, to
   avoid hunting on per-frame noise.
3. **Smoothing**: exponential moving average of the centroid over the last few frames before
   computing error.
4. **Rate limit independent of detection FPS**: cap `/ptz/move` calls to roughly the motor's
   real slew time (e.g. one call per 500-750ms), configurable, regardless of
   `detection_frame_interval_seconds`. Sending faster than the hardware can act just queues
   commands and compounds drift.
5. **Wire into `DetectionPipeline._process_frame`**: when auto-track is enabled for the
   "primary" cat, call camera's `POST /ptz/move` via a small `httpx` client against a new
   `camera_control_url` setting — not through `EventIngestionService`.
6. **Track-loss handling**: once `CentroidTracker` ages a track out, stop issuing moves;
   optionally re-center or hold last position.
7. **Periodic recalibration**: call `POST /ptz/calibrate` on a schedule or on track loss, since
   the angle estimate drifts over time by design (see `PTZController`'s module docstring).
8. **New `cat-sentinel` settings**: `autotrack_enabled`, `autotrack_min_interval_seconds`,
   `autotrack_deadband_ratio`, `autotrack_kp_pan`, `autotrack_kp_tilt`, `camera_control_url`.
9. **Control surface**: a `tracking/` package (router/schema/service, per ADR 0001's five-file
   convention) to start/stop auto-tracking per cat, e.g. `POST /cats/{id}/autotrack`.

### Deferred, separate concern
Pushing live pan/tilt/tracker state to `hub_frontend`'s `/live` page over a socket (instead of
polling `hub`'s `GET /trackers`) is a legitimate future improvement — but it's server→browser UI
fan-out, structurally similar to `AnnotatedFrameBroadcaster`'s pub/sub, not the
`cat-sentinel` → `camera` control link this ADR covers. Not required for auto-tracking to work.

## Consequences
- No new transport/protocol to build, test, or operate — reuses the existing `PTZController`
  and its `asyncio.to_thread`-wrapped, non-blocking HTTP surface.
- Tracking quality is gated by tuning (Kp, deadband, rate limit) against real hardware, not by
  network latency — expect an iteration pass with the physical camera before this feels smooth.
- `cat-sentinel` gains a new direct HTTP dependency on `camera`'s control API beyond
  `/video`/`/snapshot` and `/events/trigger`; acceptable since `camera` already exists to be
  called this way, and it keeps the CV/hardware boundary from ADR 0002 intact (`cat-sentinel`
  decides *where* to point, `camera` is still the only thing that knows *how* to move the
  motor).
- If Tapo firmware ever exposes real position feedback or a lower-latency control channel,
  revisit — but under today's open-loop, seconds-per-move hardware, HTTP is not the limiting
  factor.
