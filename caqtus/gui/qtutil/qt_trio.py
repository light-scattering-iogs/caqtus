import sys
from collections.abc import Callable, Awaitable
from typing import Optional, TypeVar, ParamSpec

import trio
from PySide6.QtCore import QObject, QEvent, QEventLoop
from PySide6.QtWidgets import QApplication
from outcome import Outcome


class _ReenterQtEvent(QEvent):
    def __init__(self, fn):
        super().__init__(QEvent.Type(QEvent.Type.User + 1))
        self.fn = fn


class _ReenterQtObject(QObject):
    def event(self, event):
        if event.type() == QEvent.Type.User + 1:
            assert isinstance(event, _ReenterQtEvent)
            event.fn()
            return True
        return False


_T = TypeVar("_T")
_P = ParamSpec("_P")


def run(
    async_fn: Callable[_P, Awaitable[_T]], *args: _P.args, **kwargs: _P.kwargs
) -> _T:
    """Run a Trio function in a Qt application.

    This function will run the given Trio function in the Qt event loop by spawning a
    trio loop in guest mode.
    It will block until the function completes.

    There is no need to call QApplication.exec() as this function will call it for you.

    If the function finishes successfully, the application quits and the function
    result is returned.
    If the function raises an exception, the application quits and the exception is
    raised.
    If the application is closed before the function completes, the function is
    cancelled and remaining tasks can finish before the application quits.
    """

    reenter_qt_object = _ReenterQtObject()

    outcome: Optional[Outcome] = None

    cancel_scope = trio.CancelScope()

    app = QApplication.instance()

    if app is None:
        raise RuntimeError("No QApplication instance found")

    async def wrap():
        with cancel_scope:
            await async_fn(*args, **kwargs)

    def run_sync_soon_threadsafe(fn):
        app.postEvent(reenter_qt_object, _ReenterQtEvent(fn))

    # This callback takes care of closing the QApplication when the trio function
    # completes.
    def done_callback(trio_main_outcome: Outcome):
        nonlocal outcome
        outcome = trio_main_outcome
        app.quit()

    trio.lowlevel.start_guest_run(
        wrap,
        run_sync_soon_threadsafe=run_sync_soon_threadsafe,
        done_callback=done_callback,
    )

    # We also need to handle the case where the application is closed before the
    # trio loop completes.
    def on_app_about_to_quit():
        cancel_scope.cancel()
        while outcome is None:
            app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    app.aboutToQuit.connect(on_app_about_to_quit)

    previous_excepthook = sys.excepthook

    exception_raised = None

    def excepthook(*args):
        nonlocal exception_raised
        exception_raised = args[1]
        app.exit(-1)

    try:
        sys.excepthook = excepthook
        app.exec()
    finally:
        sys.excepthook = previous_excepthook
        app.aboutToQuit.disconnect(on_app_about_to_quit)

    if outcome is None:
        raise RuntimeError("Application exited before trio loop completed")

    try:
        if exception_raised is not None:
            raise RuntimeError(
                "An exception occurred in a Qt slot"
            ) from exception_raised
    except:
        outcome.unwrap()
        raise
    else:
        return outcome.unwrap()
