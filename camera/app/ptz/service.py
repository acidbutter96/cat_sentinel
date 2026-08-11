"""PTZController: drives the Tapo C200's physical pan/tilt motor via pytapo.

IMPORTANT CAVEAT -- read before trusting the angles this reports:
Tapo cameras do not implement ONVIF absolute positioning or position
feedback. pytapo's underlying `motorMove` RPC takes a target x/y in the
camera's own internal coordinate plane, not degrees, and there is no query
that reports the motor's actual current position. Angle control here is
therefore *open-loop*: this class tracks an estimated pan/tilt in degrees
starting from (0, 0) at the last calibration, and converts angle deltas to
x/y coordinates using `settings.ptz_units_per_degree` (an empirically-tuned
constant -- there is no documented, model-guaranteed conversion factor).
The estimate drifts over time (motor slip, camera reboot, manual moves from
the Tapo app); call calibrate() to send the motor back to its calibrated
home position and reset the estimate to (0, 0).

pytapo is a synchronous, `requests`-based client. Router handlers must call
these methods via `asyncio.to_thread` to avoid blocking the event loop.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from pytapo import Tapo

from app.core.decorators import log_errors

logger = logging.getLogger(__name__)


@dataclass
class PTZStatus:
    pan: float
    tilt: float


@log_errors
class PTZController:
    def __init__(self, host: str, user: str, password: str, units_per_degree: float) -> None:
        self._client = Tapo(host, user, password)
        self._units_per_degree = units_per_degree
        self._lock = threading.Lock()
        self._pan_deg = 0.0
        self._tilt_deg = 0.0

    def move_to(self, pan: float, tilt: float) -> PTZStatus:
        """Moves toward an estimated absolute (pan, tilt) in degrees by
        issuing a single relative motorMove for the delta from the last
        known estimate. See module docstring: this is open-loop and will
        drift -- call calibrate() periodically to resync.
        """
        with self._lock:
            delta_pan = pan - self._pan_deg
            delta_tilt = tilt - self._tilt_deg
            x = round(delta_pan * self._units_per_degree)
            y = round(delta_tilt * self._units_per_degree)
            if x != 0 or y != 0:
                self._client.moveMotor(x, y)
            self._pan_deg = pan
            self._tilt_deg = tilt
            return PTZStatus(pan=self._pan_deg, tilt=self._tilt_deg)

    def nudge(self, direction_deg: float) -> None:
        """Single joystick-style step in a compass direction (0 <= x < 360,
        0=clockwise/right, 90=up, 180=counter-clockwise/left, 270=down --
        matches pytapo's moveMotorStep). Does not update the tracked
        estimate: the step size is fixed by the camera firmware and unknown
        to us, so a nudge intentionally invalidates absolute-angle accuracy
        until the next calibrate() or move_to().
        """
        if not (0 <= direction_deg < 360):
            raise ValueError("direction must satisfy 0 <= direction < 360")
        self._client.moveMotorStep(direction_deg)

    def calibrate(self) -> PTZStatus:
        """Sends the motor back to its calibrated home and resets the
        tracked estimate to (0, 0).
        """
        self._client.calibrateMotor()
        with self._lock:
            self._pan_deg = 0.0
            self._tilt_deg = 0.0
            return PTZStatus(pan=self._pan_deg, tilt=self._tilt_deg)

    def status(self) -> PTZStatus:
        """Local tracked estimate only -- no round-trip to the camera."""
        with self._lock:
            return PTZStatus(pan=self._pan_deg, tilt=self._tilt_deg)

    def capability(self) -> dict:
        """Raw passthrough of pytapo's getMotorCapability(), for diagnostics."""
        return self._client.getMotorCapability()
