from typing import Self

from PyQt6.QtWidgets import QMainWindow, QWidget

from experiment.session import ExperimentSessionMaker
from sequence.runtime import Sequence
from ._sequence_analyzer import SequenceAnalyzer
from ._sequence_hierarchy_widget import SequenceHierarchyWidget
from ._watchlist_widget import WatchlistWidget
from .main_window_ui import Ui_MainWindow


class GraphPlotMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, session_maker: ExperimentSessionMaker) -> None:
        super().__init__()

        self._session_maker = session_maker

        self._sequences_analyzer = SequenceAnalyzer(session_maker)
        self._watchlist_widget = WatchlistWidget(self._sequences_analyzer)

        self._sequence_hierarchy_widget = SequenceHierarchyWidget(self._session_maker)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setupUi(self)
        self._sequences_dock.setWidget(self._sequence_hierarchy_widget)
        self._sequence_hierarchy_widget.sequence_double_clicked.connect(
            self._on_sequence_double_clicked
        )
        self._toolbox_dock.setTitleBarWidget(QWidget())
        while self._tool_box.count() > 0:
            self._tool_box.removeItem(0)
        self._tool_box.addItem(self._watchlist_widget, "Watchlist")

    def _on_sequence_double_clicked(self, sequence: Sequence) -> None:
        self._watchlist_widget.add_sequence(sequence)

    def __enter__(self) -> Self:
        self._sequences_analyzer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return self._sequences_analyzer.__exit__(exc_type, exc_val, exc_tb)
