"""Regression test for the threading excepthook.

The hook installed by `claudechic.__main__` is invoked by the Python runtime
when an unhandled exception escapes a thread. The runtime passes a
`threading.ExceptHookArgs` named-tuple whose traceback field is
`exc_traceback` (NOT `exc_tb`). A previous version of the hook accessed
`args.exc_tb`, which raises AttributeError and silently swallows the real
underlying thread exception.
"""

from __future__ import annotations

import logging
import threading

from claudechic.__main__ import _threading_excepthook


class _CaptureHandler(logging.Handler):
    """Test handler that records all emitted records."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _attach_capture():
    """Attach a capture handler to the `claudechic` logger.

    The package logger has `propagate = False`, so pytest's `caplog`
    fixture (rooted at the root logger) does not see its records.
    """
    capture = _CaptureHandler()
    capture.setLevel(logging.CRITICAL)
    logger = logging.getLogger("claudechic")
    logger.addHandler(capture)
    return capture, logger


def test_threading_excepthook_handles_real_thread_exception():
    """The hook must consume an ExceptHookArgs from a real thread without
    raising. Regression for the `args.exc_tb` typo."""
    capture, logger = _attach_capture()
    original = threading.excepthook
    threading.excepthook = _threading_excepthook
    try:

        def boom():
            raise ValueError("intentional thread crash for test")

        t = threading.Thread(target=boom, name="excepthook-test-thread")
        t.start()
        t.join(timeout=2.0)
    finally:
        threading.excepthook = original
        logger.removeHandler(capture)

    # The critical log entry must be present, with the real exception attached.
    matching = [
        rec
        for rec in capture.records
        if rec.levelname == "CRITICAL"
        and rec.exc_info is not None
        and rec.exc_info[0] is ValueError
    ]
    assert matching, (
        "Expected a CRITICAL log record with ValueError exc_info; "
        "got records: "
        + repr([(r.levelname, r.getMessage(), r.exc_info) for r in capture.records])
    )


def test_threading_excepthook_skips_keyboard_interrupt():
    """KeyboardInterrupt in a thread must not be logged as a critical error."""
    capture, logger = _attach_capture()
    try:
        args = threading.ExceptHookArgs(
            [KeyboardInterrupt, KeyboardInterrupt(), None, threading.current_thread()]
        )
        _threading_excepthook(args)
    finally:
        logger.removeHandler(capture)

    assert not any(rec.levelname == "CRITICAL" for rec in capture.records)
