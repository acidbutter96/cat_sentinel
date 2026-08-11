from __future__ import annotations

from app.events.camera_command_dispatcher import (
    LoggingCameraCommandDispatcher,
    TapoCameraCommandDispatcher,
)
from tests.fakes import FakePTZController


def test_dispatches_ptz_move_to_controller():
    ptz = FakePTZController()
    dispatcher = TapoCameraCommandDispatcher(ptz)

    result = dispatcher.dispatch("ptz_move", {"pan": 30, "tilt": -5})

    assert result is True
    assert ptz.moves == [(30.0, -5.0)]


def test_dispatches_ptz_nudge_to_controller():
    ptz = FakePTZController()
    dispatcher = TapoCameraCommandDispatcher(ptz)

    result = dispatcher.dispatch("ptz_nudge", {"direction": 90})

    assert result is True
    assert ptz.nudges == [90.0]


def test_dispatches_ptz_calibrate_to_controller():
    ptz = FakePTZController()
    dispatcher = TapoCameraCommandDispatcher(ptz)

    result = dispatcher.dispatch("ptz_calibrate", {})

    assert result is True
    assert ptz.calibrations == 1


def test_falls_back_to_logging_dispatcher_for_unknown_command():
    ptz = FakePTZController()
    fallback = LoggingCameraCommandDispatcher()
    dispatcher = TapoCameraCommandDispatcher(ptz, fallback=fallback)

    result = dispatcher.dispatch("light_on", {"duration_seconds": 30})

    assert result is True
    assert ptz.moves == []


def test_ptz_command_failure_returns_false_without_raising():
    ptz = FakePTZController()
    dispatcher = TapoCameraCommandDispatcher(ptz)

    result = dispatcher.dispatch("ptz_move", {"pan": "not-a-number", "tilt": 0})

    assert result is False
