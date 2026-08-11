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
    assert any(r.levelname == "DEBUG" and "add" in r.getMessage() for r in caplog.records)


def test_log_call_sync_raises_and_logs_error(caplog):
    @log_call
    def boom():
        raise ValueError("kaboom")

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError, match="kaboom"):
            boom()

    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    assert error_records[0].exc_info is not None


async def test_log_call_async_logs_and_returns_value(caplog):
    @log_call
    async def add_async(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG):
        result = await add_async(2, 3)

    assert result == 5
    assert any(r.levelname == "DEBUG" and "add_async" in r.getMessage() for r in caplog.records)


async def test_log_call_async_raises_and_logs_error(caplog):
    @log_call
    async def boom_async():
        raise ValueError("async kaboom")

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError, match="async kaboom"):
            await boom_async()

    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1


def test_log_call_records_carry_event_and_target_extra(caplog):
    @log_call
    def greet():
        return "hi"

    with caplog.at_level(logging.DEBUG):
        greet()

    debug_record = next(r for r in caplog.records if r.levelname == "DEBUG")
    assert debug_record.event == "method_call"
    assert debug_record.target.endswith("greet")


def test_log_errors_wraps_public_methods_but_not_dunder_or_private(caplog):
    @log_errors
    class Dummy:
        def __init__(self):
            self.value = 0

        def public_one(self):
            return "one"

        def public_two(self):
            return "two"

        def _private(self):
            return "private"

    with caplog.at_level(logging.DEBUG):
        instance = Dummy()  # __init__ should not log
        instance.public_one()
        instance.public_two()
        instance._private()  # should not log

    targets = [r.target for r in caplog.records if r.levelname == "DEBUG" and hasattr(r, "target")]
    assert any(t.endswith("Dummy.public_one") for t in targets)
    assert any(t.endswith("Dummy.public_two") for t in targets)
    assert not any(t.endswith("Dummy._private") for t in targets)
    assert not any(t.endswith("Dummy.__init__") for t in targets)
