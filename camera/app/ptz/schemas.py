from __future__ import annotations

from pydantic import BaseModel, Field


class PTZMoveRequest(BaseModel):
    pan: float = Field(
        ..., description="Target pan angle in degrees (open-loop, camera-relative)"
    )
    tilt: float = Field(
        ..., description="Target tilt angle in degrees (open-loop, camera-relative)"
    )


class PTZNudgeRequest(BaseModel):
    direction: float = Field(
        ...,
        ge=0,
        lt=360,
        description=(
            "Compass direction for a single joystick-style step "
            "(0=clockwise/right, 90=up, 180=counter-clockwise/left, 270=down)"
        ),
    )


class PTZStatusResponse(BaseModel):
    pan: float
    tilt: float


class PTZCalibrateResponse(BaseModel):
    calibrated: bool
    pan: float
    tilt: float
