import threading
from typing import Optional, Iterable, Mapping

from PyQt6.QtCore import pyqtSignal, QSignalBlocker, QTimer, Qt, QModelIndex
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QMainWindow,
    QSpinBox,
    QSizePolicy,
)

from experiment.session import ExperimentSessionMaker
from sequence.runtime import Shot, Sequence
from sequence_hierarchy import SequenceHierarchyModel, SequenceHierarchyDelegate
from viewer.sequence_watcher import SequenceWatcher
from .single_shot_viewer import SingleShotViewer
from .single_shot_widget_ui import Ui_SingleShotWidget


class SingleShotWidget(QMainWindow, Ui_SingleShotWidget):
    def __init__(
        self,
        viewers: Mapping[str, SingleShotViewer],
        experiment_session_maker: ExperimentSessionMaker,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)
        self._model = SequenceHierarchyModel(experiment_session_maker)

        self._sequence_watcher: Optional[SequenceWatcher] = None

        self._setup_ui(viewers)
        self._experiment_session_maker = experiment_session_maker

    def _setup_ui(self, viewers: Mapping[str, SingleShotViewer]) -> None:
        self.setupUi(self)
        self.setWindowTitle("Single Shot Viewer")
        self._sequence_hierarchy_view.setModel(self._model)
        self._sequence_hierarchy_view.setItemDelegateForColumn(
            1, SequenceHierarchyDelegate()
        )
        self._sequence_hierarchy_view.doubleClicked.connect(
            self.on_sequence_double_clicked
        )
        self._sequence_hierarchy_dock.setWindowTitle("Sequences")

        # refresh the view to update the info in real time
        self.view_update_timer = QTimer(self)
        self.view_update_timer.timeout.connect(self._sequence_hierarchy_view.update)
        self.view_update_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.view_update_timer.start(500)

        self._shot_selector = ShotSelector()
        self._shot_selector.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        for name, viewer in viewers.items():
            self.add_viewer(name, viewer)

        # noinspection PyUnresolvedReferences
        self._shot_selector.shot_changed.connect(self._update_viewers)
        self._action_cascade.triggered.connect(self._mdi_area.cascadeSubWindows)
        self._action_tile.triggered.connect(self._mdi_area.tileSubWindows)
        self._shot_selector_dock.setWidget(self._shot_selector)
        self._shot_selector_dock.setTitleBarWidget(QWidget())

    def on_sequence_double_clicked(self, index: QModelIndex) -> None:
        path = self._model.get_path(index)
        if path is None:
            return
        with self._experiment_session_maker() as session:
            if not path.is_sequence(session):
                return

        sequence = Sequence(path)
        if self._sequence_watcher is not None:
            self._sequence_watcher.stop()
        self.reset()
        self._sequence_watcher = SequenceWatcher(
            sequence, target=self.add_shots, watch_interval=0.1, chunk_size=97
        )
        self._sequence_watcher.start()

    def add_shots(self, shots: Iterable[Shot]) -> None:
        self._shot_selector.add_shots(shots)
        self._update_viewers(self._shot_selector.get_selected_shot())

    def add_viewer(self, name: str, viewer: SingleShotViewer) -> None:
        subwindow = self._mdi_area.addSubWindow(viewer)
        subwindow.setWindowTitle(name)

    def reset(self) -> None:
        self._shot_selector.reset()

    def _update_viewers(self, shot) -> None:
        for viewer in self._get_viewers().values():
            viewer.set_shot(shot)
        for viewer in self._get_viewers().values():
            viewer.update_view()

    def _get_viewers(self) -> dict[str, SingleShotViewer]:
        return {
            subwindow.windowTitle(): subwindow.widget()
            for subwindow in self._mdi_area.subWindowList()
        }


class ShotSelector(QWidget):
    shot_changed = pyqtSignal(Shot)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self._lock = threading.Lock()
        self.setLayout(QHBoxLayout())

        self._shots: list[Shot] = []
        self._shot_spinbox = QSpinBox()
        self._shot_spinbox.setMinimum(0)
        self._shot_spinbox.valueChanged.connect(self.on_shot_spinbox_value_changed)
        self.layout().addWidget(self._shot_spinbox)

        self._current_shot = -1
        self.update_spinbox()

        self._left_button = QPushButton("<")
        self._left_button.setAutoRepeat(True)
        self._left_button.setAutoRepeatInterval(100)
        self._left_button.clicked.connect(self.on_left_button_clicked)
        self.layout().addWidget(self._left_button)

        self._pause_button = QPushButton("||")
        self._pause_button.clicked.connect(self.on_pause_button_clicked)
        self.layout().addWidget(self._pause_button)

        self._right_button = QPushButton(">")
        self._right_button.setAutoRepeat(True)
        self._right_button.setAutoRepeatInterval(100)
        self._right_button.clicked.connect(self.on_right_button_clicked)
        self.layout().addWidget(self._right_button)

        self._last_button = QPushButton(">>")
        self._last_button.clicked.connect(self.on_last_button_clicked)
        self.layout().addWidget(self._last_button)
        # noinspection PyUnresolvedReferences
        self.layout().addStretch()

    def add_shots(self, shots: Iterable[Shot]) -> None:
        with self._lock:
            self._shots.extend(shots)
            self.update_spinbox()

    def get_selected_shot(self) -> Shot:
        return self._shots[self._current_shot]

    def on_left_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1

        self._current_shot = max(0, self._current_shot - 1)
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.shot_changed.emit(self.get_selected_shot())

    def on_right_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1

        self._current_shot = min(len(self._shots) - 1, self._current_shot + 1)
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.shot_changed.emit(self.get_selected_shot())

    def on_last_button_clicked(self) -> None:
        self._current_shot = -1
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.shot_changed.emit(self.get_selected_shot())

    def on_pause_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.shot_changed.emit(self.get_selected_shot())

    def on_shot_spinbox_value_changed(self, value: int) -> None:
        self._current_shot = value - 1
        # noinspection PyUnresolvedReferences
        self.shot_changed.emit(self.get_selected_shot())

    def update_spinbox(self) -> None:
        if self._current_shot == -1:
            current_shot = len(self._shots) - 1
        else:
            current_shot = self._current_shot
        with QSignalBlocker(self._shot_spinbox):
            self._shot_spinbox.setMaximum(len(self._shots))
            self._shot_spinbox.setValue(current_shot + 1)
            self._shot_spinbox.setSuffix(f"/{len(self._shots)}")
            self._shot_spinbox.setPrefix("Shot: ")

    def reset(self) -> None:
        self._current_shot = -1
        self._shots = []
        self.update_spinbox()
