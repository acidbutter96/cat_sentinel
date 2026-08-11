import logging

import pytest

from app.core.decorators import log_call, log_errors


def test_log_call_sync_logs_debug_and_returns_value(caplog):
    @log_call
    def add(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG):
        result = add(1, 2)

    assert result == 3
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("add" in r.getMessage() for r in debug_records)


def test_log_call_sync_raises_and_logs_error(caplog):
    @log_call
    def boom():
        raise ValueError("kaboom")

    with caplog.at_level(logging.DEBUG), pytest.raises(ValueError):
        boom()

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert error_records[0].exc_info is not None


async def test_log_call_async_returns_value_and_logs(caplog):
    @log_call
    async def add(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG):
        result = await add(2, 3)

    assert result == 5
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("add" in r.getMessage() for r in debug_records)


def test_log_call_records_carry_event_and_target(caplog):
    @log_call
    def noop():
        return None

    with caplog.at_level(logging.DEBUG):
        noop()

    record = next(r for r in caplog.records if r.levelno == logging.DEBUG)
    assert record.event == "method_call"
    assert "noop" in record.target


def test_log_errors_wraps_public_methods_not_dunders_or_private(caplog):
    @log_errors
    class Dummy:
        def __init__(self):
            self.value = 1

        def public_a(self):
            return "a"

        def public_b(self):
            return "b"

        def _private(self):
            return "private"

    with caplog.at_level(logging.DEBUG):
        dummy = Dummy()
        dummy.public_a()
        dummy.public_b()
        dummy._private()

    messages = [r.getMessage() for r in caplog.records]
    assert any("Dummy.public_a called" in m for m in messages)
    assert any("Dummy.public_b called" in m for m in messages)
    assert not any("Dummy.__init__" in m for m in messages)
    assert not any("Dummy._private" in m for m in messages)
