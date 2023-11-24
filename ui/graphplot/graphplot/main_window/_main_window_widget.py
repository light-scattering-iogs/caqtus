import contextlib
import threading
from collections.abc import Mapping
from typing import Self, Any, Optional

from PyQt6.QtWidgets import QMainWindow, QWidget

from analyza.loading.importers import ShotImporter
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.runtime import Sequence, Shot
from util.concurrent import BackgroundScheduler
from .main_window_ui import Ui_MainWindow
from .._data_loader_selector import DataLoaderSelector
from .._sequence_analyzer import SequenceAnalyzer, DataImporter
from .._sequence_hierarchy_widget import SequenceHierarchyWidget
from .._watchlist_widget import WatchlistWidget
from ..visualizer_creator import VisualizerCreator, Visualizer
from ..visualizer_creators_selector import VisualizerCreatorSelector


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

        self._exit_stack = contextlib.ExitStack()
        self._sequences_analyzer = SequenceAnalyzer(session_maker)
        self._background_scheduler = BackgroundScheduler(max_workers=1)
        self._watchlist_widget = WatchlistWidget(self._sequences_analyzer)
        self._data_loader_selector = DataLoaderSelector(data_loaders)
        self._visualizer_selector = VisualizerCreatorSelector(visualizer_creators)
        self._data_loader: DataImporter = import_nothing
        self._visualizer: Optional[Visualizer] = None

        self._sequence_hierarchy_widget = SequenceHierarchyWidget(self._session_maker)
        self._current_visualizer_lock = threading.Lock()
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
        self._visualizer_selector.visualizer_selected.connect(
            self.change_current_visualizer
        )

    def _on_data_loader_selected(self, data_loader: DataImporter) -> None:
        self._data_loader = data_loader
        for sequence in self._sequences_analyzer.sequences:
            self._sequences_analyzer.monitor_sequence(sequence, self._data_loader)

    def _on_sequence_double_clicked(self, sequence: Sequence) -> None:
        self._watchlist_widget.add_sequence(sequence, self._data_loader)

    def change_current_visualizer(self, visualizer: Visualizer) -> None:
        """Sets a new visualizer for the central widget."""

        # Here we loose all references to the old visualizer, so it will be freed. To avoid having functions running on
        # the old visualizer while it's being freed, we put all accesses to the current visualizer behind a lock.
        with self._current_visualizer_lock:
            self._visualizer = visualizer
            self.setCentralWidget(self._visualizer)

    def __enter__(self) -> Self:
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._sequences_analyzer)
        self._exit_stack.enter_context(self._background_scheduler)
        self._background_scheduler.schedule_task(self._update_visualizer, 0.5)
        return self

    def _update_visualizer(self) -> None:
        """Feed new data to the current visualizer."""

        if self._visualizer is not None:
            dataframe = self._sequences_analyzer.get_dataframe()
            # Here we put a lock to ensure that sel._visualize won't be reassigned while it is processing some
            # data. The issue is that if we loose all references on the visualizer while it is processing data in
            # another thread, the C++ parts of a widget will be freed while they are still being used.
            with self._current_visualizer_lock:
                self._visualizer.update_data(dataframe)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return self._exit_stack.__exit__(exc_type, exc_val, exc_tb)
