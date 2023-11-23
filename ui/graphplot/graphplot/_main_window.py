from typing import Self

from PyQt6.QtWidgets import QMainWindow

from experiment.session import ExperimentSessionMaker
from ._sequence_analyzer import SequenceAnalyzer
from ._sequence_hierarchy_widget import SequenceHierarchyWidget
from .main_window_ui import Ui_MainWindow


class GraphPlotMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, session_maker: ExperimentSessionMaker) -> None:
        super().__init__()

        self._session_maker = session_maker
        self._sequences_analyzer = SequenceAnalyzer(session_maker)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        self._sequences_dock.setWidget(SequenceHierarchyWidget(self._session_maker))

    def __enter__(self) -> Self:
        self._sequences_analyzer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return self._sequences_analyzer.__exit__(exc_type, exc_val, exc_tb)
