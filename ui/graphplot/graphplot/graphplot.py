import asyncio
import logging
from typing import Self

import PySide6.QtAsyncio as QtAsyncio
import qtawesome
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QLabel

from core.session import ExperimentSessionMaker
from sequence_hierarchy import PathHierarchyView
from graphplot.data_loading import DataLoader

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
        """
        Args:
            session_maker: A callable used to create sessions from which the application can retrieve data.
        """

        self.app = QApplication(*args)
        self.app.setApplicationName("GraphPlot")
        self.app.setStyle("Fusion")
        self.app.setWindowIcon(qtawesome.icon("mdi6.chart-line", size=64))
        self.main_window = GraphPlotMainWindow(session_maker)

    def run(self) -> None:
        with self.main_window:
            self.main_window.show()
            QtAsyncio.run()


class GraphPlotMainWindow(QMainWindow):
    """The main window for the GraphPlot application.

    On the left, it displays a tree view of the experiment session's sequences.
    On the right, there is a widget to define how to import data from the sequences.
    In the middle, there is a view of the data loaded from the sequences.
    """

    def __init__(self, session_maker: ExperimentSessionMaker, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.splitter = QSplitter(self)
        self.setCentralWidget(self.splitter)
        self.session_maker = session_maker
        self.path_view = PathHierarchyView(self.session_maker, self)
        self.loader = DataLoader(session_maker, self)
        self.path_view.sequence_double_clicked.connect(self.loader.add_sequence_to_watchlist)
        self.splitter.addWidget(self.path_view)
        self.splitter.addWidget(self.loader)

    def __enter__(self) -> Self:
        self.path_view.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return self.path_view.__exit__(exc_type, exc_val, exc_tb)
