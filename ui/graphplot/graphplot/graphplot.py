import asyncio
import logging
from typing import Self

import PySide6.QtAsyncio as QtAsyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QLabel

from core.session import ExperimentSessionMaker

logger = logging.getLogger(__name__)


async def wrap(coro):
    # noinspection PyBroadException
    try:
        return await coro
    except Exception:
        logger.critical("Unhandled exception", exc_info=True)
        loop = asyncio.get_event_loop()
        loop.stop()


class GraphPlot:
    def __init__(self, session_maker: ExperimentSessionMaker, *args) -> None:
        self.app = QApplication(*args)
        self.app.setApplicationName("GraphPlot")
        self.main_window = GraphPlotMainWindow()
        self.session_maker = session_maker

    def run(self) -> None:
        with self.main_window:
            self.main_window.show()
            QtAsyncio.run()


class GraphPlotMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.splitter = QSplitter(self)
        self.setCentralWidget(self.splitter)
        self.splitter.addWidget(QLabel("Hello"))
        self.splitter.addWidget(QLabel("World"))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False
