from typing import Callable, Optional, ParamSpec, TypeVar

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import QWidget, QMessageBox

P = ParamSpec("P")
T = TypeVar("T")


class WorkerThread(QThread):
    def __init__(self, function: Callable[[P], T], *args: P.args, **kwargs: P.kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.exception = None
        self.result: Optional[T] = None

    def run(self):
        def _run():
            try:
                self.result = self.function(*self.args, **self.kwargs)
            except Exception as e:
                self.exception = e
            finally:
                self.finished.emit()

        return _run()


def run_with_wip_widget(
    parent: QWidget,
    msg: str,
    function: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    message_box = QMessageBox(parent)
    message_box.setText(msg)
    message_box.setWindowFlags(
        (message_box.windowFlags() | Qt.WindowType.Window.CustomizeWindowHint)
        & Qt.WindowType.Window.FramelessWindowHint
    )
    worker = WorkerThread(function, *args, **kwargs)
    worker.finished.connect(message_box.close)
    worker.start()
    message_box.exec()
    if worker.exception is not None:
        raise worker.exception
    return worker.result
