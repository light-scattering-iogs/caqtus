from collections.abc import Mapping
from typing import Self, Any

from PyQt6.QtWidgets import QMainWindow, QWidget

from analyza.loading.importers import ShotImporter
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.runtime import Sequence, Shot
from ._data_loader_selector import DataLoaderSelector
from ._sequence_analyzer import SequenceAnalyzer, DataImporter
from ._sequence_hierarchy_widget import SequenceHierarchyWidget
from ._watchlist_widget import WatchlistWidget
from .main_window_ui import Ui_MainWindow
from .visualizer_creator import VisualizerCreator, Visualizer
from .visualizer_creators_selector import VisualizerCreatorSelector


def import_nothing(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return {}


class GraphPlotMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        data_loaders: Mapping[str, ShotImporter],
        visualizer_creators: Mapping[str, VisualizerCreator],
    ) -> None:
        super().__init__()

        self._session_maker = session_maker

        self._sequences_analyzer = SequenceAnalyzer(session_maker)
        self._watchlist_widget = WatchlistWidget(self._sequences_analyzer)
        self._data_loader_selector = DataLoaderSelector(data_loaders)
        self._visualizer_selector = VisualizerCreatorSelector(visualizer_creators)
        self._data_loader: DataImporter = import_nothing

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
        self._tool_box.addItem(self._data_loader_selector, "Data loading")
        self._data_loader_selector.data_loader_selected.connect(
            self._on_data_loader_selected
        )
        self._tool_box.addItem(self._visualizer_selector, "Visualization")
        self._visualizer_selector.visualizer_selected.connect(self._on_visualizer_selected)

    def _on_data_loader_selected(self, data_loader: DataImporter) -> None:
        self._data_loader = data_loader
        for sequence in self._sequences_analyzer.sequences:
            self._sequences_analyzer.monitor_sequence(sequence, self._data_loader)

    def _on_sequence_double_clicked(self, sequence: Sequence) -> None:
        self._watchlist_widget.add_sequence(sequence, self._data_loader)

    def _on_visualizer_selected(self, visualizer: Visualizer) -> None:
        pass

    def __enter__(self) -> Self:
        self._sequences_analyzer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return self._sequences_analyzer.__exit__(exc_type, exc_val, exc_tb)
