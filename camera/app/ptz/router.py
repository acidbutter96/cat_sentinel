"""Pan/tilt control for the Tapo C200's physical motor, via pytapo. See
app/ptz/service.py for the open-loop angle-tracking caveat -- there is no
absolute position feedback from the camera.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.core.dependencies import PTZControllerDep
from app.core.exceptions import InvalidRequestError
from app.ptz.schemas import (
    PTZCalibrateResponse,
    PTZMoveRequest,
    PTZNudgeRequest,
    PTZStatusResponse,
)

router = APIRouter(prefix="/ptz", tags=["ptz"])


@router.post(
    "/move", response_model=PTZStatusResponse, summary="Move to an estimated pan/tilt angle"
)
async def move(payload: PTZMoveRequest, ptz: PTZControllerDep) -> PTZStatusResponse:
    status = await asyncio.to_thread(ptz.move_to, payload.pan, payload.tilt)
    return PTZStatusResponse(pan=status.pan, tilt=status.tilt)


@router.post(
    "/nudge",
    response_model=PTZStatusResponse,
    summary="Single joystick-style step in a compass direction",
)
async def nudge(payload: PTZNudgeRequest, ptz: PTZControllerDep) -> PTZStatusResponse:
    try:
        await asyncio.to_thread(ptz.nudge, payload.direction)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc
    status = ptz.status()
    return PTZStatusResponse(pan=status.pan, tilt=status.tilt)


@router.post(
    "/calibrate",
    response_model=PTZCalibrateResponse,
    summary="Recalibrate the motor and reset the tracked estimate to (0, 0)",
)
async def calibrate(ptz: PTZControllerDep) -> PTZCalibrateResponse:
    status = await asyncio.to_thread(ptz.calibrate)
    return PTZCalibrateResponse(calibrated=True, pan=status.pan, tilt=status.tilt)


@router.get(
    "/status",
    response_model=PTZStatusResponse,
    summary="Last known estimated pan/tilt (local state, no camera round-trip)",
)
async def status_(ptz: PTZControllerDep) -> PTZStatusResponse:
    status = ptz.status()
    return PTZStatusResponse(pan=status.pan, tilt=status.tilt)
