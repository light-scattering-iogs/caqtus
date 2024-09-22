from collections.abc import Callable, Awaitable
from typing import Optional

import anyio
from PySide6 import QtWidgets

from caqtus.gui.qtutil import temporary_widget


async def blocking_call[
    **P, T
](
    parent: Optional[QtWidgets.QWidget],
    msg: str,
    fun: Callable[P, Awaitable[T]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> None:
    """Run an async function while blocking the application with a message box.

    When the function terminates, the message box is closed and the user can resume
    interacting with the application.

    If the cancel button of the message box is clicked, the function will be cancelled.
    The message box will be closed immediately, but the function will continue to run
    until it reaches a cancellation point.

    It is the responsibility of the function to check for cancellation and handle it
    appropriately.

    Args:
        parent: The parent widget for the message box.
        msg: The message to display in the message box.
        fun: The async function to run.
        args: The arguments to pass to the function.
        kwargs: The keyword arguments to pass to the function
    """

    cancel_scope = anyio.CancelScope()

    def on_finished(result: QtWidgets.QDialog.DialogCode):
        if result == QtWidgets.QMessageBox.StandardButton.Cancel:
            cancel_scope.cancel()

    with temporary_widget(QtWidgets.QMessageBox(parent)) as message_box:

        async def wrapped():
            with cancel_scope:
                ret = await fun(*args, **kwargs)
                message_box.accept()
                return ret

        message_box.setText(msg)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Cancel)
        message_box.finished.connect(on_finished)

        async with anyio.create_task_group() as tg:
            tg.start_soon(wrapped)
            message_box.open()
