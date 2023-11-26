import contextlib
import logging
import threading
from collections.abc import Mapping
from typing import Self, Optional

import polars
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMainWindow, QProgressBar
from pyqtgraph.dockarea import DockArea, Dock

from core.session import ExperimentSessionMaker, ExperimentSession, Sequence, Shot
from util.concurrent import BackgroundScheduler
from ._main_window_ui import Ui_MainWindow
from .._sequence_hierarchy_widget import SequenceHierarchyWidget
from ..data_loading import DataLoaderSelector, DataImporter, ShotData
from ..sequence_analyzer import SequenceAnalyzer
from ..visualization import VisualizerCreator, Visualizer, VisualizerCreatorSelector
from ..watchlist import WatchlistWidget

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def import_nothing(shot: Shot, session: ExperimentSession) -> ShotData:
    return polars.DataFrame()


class GraphPlotMainWindow(QMainWindow, Ui_MainWindow):
    """Main window of GraphPlot.

    This is a main window widget used to plot graphs about a sequence (or collection of sequences). This widget has a
    dock on the left showing the sequence hierarchy from which the user can choose which sequences to watch. It also
    has a dock on the right with a tab for the sequence watchlist, another tab to choose how to import the data from a
    shot and a last tab to choose how to visualize the data. The central widget contains the actual visualization for
    the data of the sequences.
    """

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        data_loaders: Mapping[str, DataImporter],
        visualizer_creators: Mapping[str, VisualizerCreator],
    ) -> None:
        """Initialize a new GraphPlotMainWindow.

        Args:
            session_maker: An object that can create sessions containing access to the permanent storage of the
                experiment. The sequence hierarchy and the data from the shots are pulled from sessions created by this
                object.
            data_loaders: A mapping of shot importers that can be chosen from to load data from the shots.
            visualizer_creators: A mapping of objects that can create the central widget. User can choose from an
                element of this mapping to display information about sequences.
        """

        super().__init__()

        self._session_maker = session_maker

        self._exit_stack = contextlib.ExitStack()
        self._sequences_analyzer = SequenceAnalyzer(session_maker)
        self._background_scheduler = BackgroundScheduler(max_workers=1)
        self._watchlist_widget = WatchlistWidget(self._sequences_analyzer)
        self._data_loader_selector = DataLoaderSelector(data_loaders)
        self._visualizer_selector = VisualizerCreatorSelector(visualizer_creators)
        self._data_loader: DataImporter = import_nothing
        self._view: Optional[Visualizer] = None

        self._sequence_hierarchy_widget = SequenceHierarchyWidget(self._session_maker)
        self._current_visualizer_lock = threading.Lock()
        self._loading_bar = QProgressBar()
        self._loading_bar_timer = QTimer(self)
        self._setup_ui()

        self._update_view_timer = QTimer(self)
        self._update_view_timer.singleShot(500, self._update_view)

    def _setup_ui(self) -> None:
        self.setupUi(self)
        self._dock_area = DockArea()

        # Sets up a dock on the left containing the sequence hierarchy
        self._sequence_hierarchy_dock = Dock("Sequences", closable=False)
        self._sequence_hierarchy_dock.addWidget(self._sequence_hierarchy_widget)
        self._sequence_hierarchy_widget.sequence_double_clicked.connect(
            self._on_sequence_double_clicked
        )
        self._dock_area.addDock(self._sequence_hierarchy_dock, "left")

        self._visualizer_dock = Dock("View", closable=False)
        self._dock_area.addDock(
            self._visualizer_dock, "right", relativeTo=self._sequence_hierarchy_dock
        )

        self._watchlist_dock = Dock("Watchlist", closable=False)
        self._watchlist_dock.addWidget(self._watchlist_widget)
        self._dock_area.addDock(
            self._watchlist_dock, "right", relativeTo=self._visualizer_dock
        )

        self._data_lading_dock = Dock("Data loading", closable=False)
        self._data_lading_dock.addWidget(self._data_loader_selector)
        self._dock_area.addDock(
            self._data_lading_dock, "bottom", relativeTo=self._watchlist_dock
        )
        self._data_loader_selector.data_loader_selected.connect(
            self._on_data_loader_selected
        )

        self._visualizer_creator_dock = Dock("View selection", closable=False)
        self._visualizer_creator_dock.addWidget(self._visualizer_selector)
        self._dock_area.addDock(
            self._visualizer_creator_dock, "bottom", relativeTo=self._data_lading_dock
        )
        self._visualizer_selector.visualizer_selected.connect(
            self.change_current_visualizer
        )

        self.setCentralWidget(self._dock_area)

        self._status_bar.addPermanentWidget(self._loading_bar)
        self._loading_bar_timer.timeout.connect(self._update_loading_bar)  # type: ignore
        self._loading_bar_timer.start(50)

    def _update_loading_bar(self) -> None:
        current, maximum = self._sequences_analyzer.get_progress()
        if maximum == 0:
            current = 0
            maximum = 1
        self._loading_bar.setValue(current)
        self._loading_bar.setMaximum(maximum)

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
            self._view = visualizer
            while self._visualizer_dock.layout.count() > 0:
                self._visualizer_dock.layout.itemAt(0).widget().setParent(None)
            self._visualizer_dock.addWidget(self._view)

    def __enter__(self) -> Self:
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._sequences_analyzer)
        self._exit_stack.enter_context(self._background_scheduler)
        # self._background_scheduler.schedule_task(self._update_visualizer, 1)
        return self

    def _update_view(self) -> None:
        """Feed new data to the current visualizer."""

        if self._view is not None:
            dataframe = self._sequences_analyzer.get_dataframe()
            # Here we put a lock to ensure that sel._visualize won't be reassigned while it is processing some
            # data. The issue is that if we loose all references on the visualizer while it is processing data in
            # another thread, the C++ parts of a widget will be freed while they are still being used.
            with self._current_visualizer_lock:
                # noinspection PyBroadException
                try:
                    # Here we call the view code, which is not in our control. If it crashes, we want to catch the
                    # exception and log it, but we don't want to crash the whole program.
                    self._view.update_data(dataframe)
                except Exception:
                    logger.error("Error while updating view", exc_info=True)
        self._update_view_timer.singleShot(500, self._update_view)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return self._exit_stack.__exit__(exc_type, exc_val, exc_tb)
