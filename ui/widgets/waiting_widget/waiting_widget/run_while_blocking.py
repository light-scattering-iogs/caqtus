from typing import Callable, Optional

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtWidgets import QWidget, QDialog, QMessageBox


class WorkerThread(QThread):
    def __init__[
        **P, T
    ](self, function: Callable[[P], T], *args: P.args, **kwargs: P.kwargs):
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


class BlockingWidget(QDialog):
    def __init__(self, msg: str, parent: QWidget):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)


def run_with_wip_widget[
    **P, T
](
    parent: QWidget,
    msg: str,
    function: Callable[[P], T],
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
