from __future__ import annotations

import logging

import pytest

from app.core.decorators import log_call, log_errors


def test_log_call_sync_logs_debug_and_returns_value(caplog):
    @log_call
    def add(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG):
        result = add(2, 3)

    assert result == 5
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert any("add" in r.getMessage() for r in debug_records)


def test_log_call_sync_raises_and_logs_error(caplog):
    @log_call
    def boom():
        raise ValueError("kaboom")

    with caplog.at_level(logging.DEBUG), pytest.raises(ValueError, match="kaboom"):
        boom()

    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    assert error_records[0].exc_info is not None


async def test_log_call_async_returns_value_and_logs(caplog):
    @log_call
    async def add(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG):
        result = await add(2, 3)

    assert result == 5
    assert any(r.levelname == "DEBUG" for r in caplog.records)


async def test_log_call_async_raises_and_logs_error(caplog):
    @log_call
    async def boom():
        raise ValueError("kaboom")

    with caplog.at_level(logging.DEBUG), pytest.raises(ValueError, match="kaboom"):
        await boom()

    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1


def test_log_call_extra_fields(caplog):
    @log_call
    def foo():
        return None

    with caplog.at_level(logging.DEBUG):
        foo()

    record = next(r for r in caplog.records if r.levelname == "DEBUG")
    assert record.event == "method_call"
    assert "foo" in record.target


def test_log_errors_wraps_public_methods_not_dunders_or_private(caplog):
    @log_errors
    class Dummy:
        def __init__(self):
            self.value = 1

        def public_method(self):
            return self.value

        def other_public(self):
            return self.value * 2

        def _private(self):
            return "hidden"

    with caplog.at_level(logging.DEBUG):
        dummy = Dummy()
        caplog.clear()
        dummy.public_method()
        dummy.other_public()
        dummy._private()

    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    logged_targets = {r.target for r in debug_records if hasattr(r, "target")}
    assert any(t.endswith("Dummy.public_method") for t in logged_targets)
    assert any(t.endswith("Dummy.other_public") for t in logged_targets)
    assert not any(t.endswith("Dummy._private") for t in logged_targets)
