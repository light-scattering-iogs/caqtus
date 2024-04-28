import collections
import functools
from typing import Optional, Mapping, assert_never

from PySide6.QtCore import Signal, QSignalBlocker, QSettings, QObject
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QMainWindow,
    QSpinBox,
    QFileDialog,
    QSizePolicy,
)
from pyqtgraph.dockarea import DockArea, Dock

from caqtus.gui.common.sequence_hierarchy import PathHierarchyView
from caqtus.session import ExperimentSessionMaker, PureSequencePath
from caqtus.session._return_or_raise import unwrap
from caqtus.session.sequence import Shot
from caqtus.utils import serialization
from caqtus.utils.concurrent import BackgroundScheduler
from .main_window_ui import Ui_ShotViewerMainWindow
from .workspace import ViewState, WorkSpace
from ..single_shot_viewers import ShotView, ViewManager, ManagerName


class ShotViewerMainWindow(QMainWindow, Ui_ShotViewerMainWindow):
    current_shot_changed = Signal(Shot)
    shots_changed = Signal()

    def __init__(
        self,
        experiment_session_maker: ExperimentSessionMaker,
        view_managers: Mapping[str, ViewManager],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        # self._sequence_watcher: Optional[SequenceWatcher] = None

        self._views: dict[str, tuple[ManagerName, ShotView]] = {}
        self._experiment_session_maker = experiment_session_maker
        self._view_managers = view_managers
        self._dock_area = DockArea()
        self._sequence_widget = PathHierarchyView(self._experiment_session_maker)
        self._shot_selector: ShotSelector = ShotSelector()
        self._sequence_watcher = SequenceWatcher(self._experiment_session_maker)

        self._setup_ui()
        self.restore_state()

    def __enter__(self):
        self._sequence_watcher.__enter__()
        self._sequence_widget.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sequence_widget.__exit__(exc_type, exc_val, exc_tb)
        return self._sequence_watcher.__exit__(exc_type, exc_val, exc_tb)

    def restore_state(self):
        ui_settings = QSettings("Caqtus", "ShotViewer")
        self.restoreState(ui_settings.value("state", self.saveState()))
        self.restoreGeometry(ui_settings.value("geometry", self.saveGeometry()))

    def closeEvent(self, a0):
        ui_settings = QSettings("Caqtus", "ShotViewer")
        ui_settings.setValue("state", self.saveState())
        ui_settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(a0)

    def _setup_ui(self) -> None:
        self.setupUi(self)
        self._add_default_docks()

        self.action_save_workspace_as.triggered.connect(self.save_workspace_as)
        self.action_load_workspace.triggered.connect(self.load_workspace)

        self._add_view_managers(self._view_managers)

        self.setWindowTitle("Single Shot Viewer")
        self.setCentralWidget(self._dock_area)

    def _add_default_docks(self) -> None:
        sequence_dock = Dock("Sequences")
        self._sequence_widget.sequence_double_clicked.connect(
            self.on_sequence_double_clicked
        )
        sequence_dock.addWidget(self._sequence_widget)
        self._dock_area.addDock(sequence_dock, "left")

        self._shot_selector = ShotSelector()
        self._sequence_watcher.shots_changed.connect(self._shot_selector.on_shots_changed)  # type: ignore
        self._shot_selector.current_shot_changed.connect(self._update_views)  # type: ignore
        self._shot_selector.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        # noinspection PyUnresolvedReferences
        shot_selector_dock = Dock("Shot")
        # shot_selector_dock.hideTitleBar()
        shot_selector_dock.addWidget(self._shot_selector)
        self._dock_area.addDock(shot_selector_dock, "top", relativeTo=sequence_dock)

    def _add_view_managers(self, view_managers: Mapping[str, ViewManager]) -> None:
        for name in view_managers:
            self.menu_add_view.addAction(name).triggered.connect(
                functools.partial(self._create_view, name)
            )

    def _create_view(self, manager_name: ManagerName) -> None:
        manager = self._view_managers[manager_name]
        created = manager.state_generator(self)
        match created:
            case None:
                return
            case (view_name, view_state):
                view = manager.constructor(view_state)
                self._add_view(manager_name, view_name, view)
            case _:
                assert_never(created)

    def _add_view(
        self, constructor_name: ManagerName, view_name: str, view: ShotView
    ) -> None:
        self._views[view_name] = (constructor_name, view)
        dock = Dock(view_name)
        dock.addWidget(view)
        self._dock_area.addDock(dock, "right")

    def get_workspace(self) -> WorkSpace:
        views = {}
        for view_name, (manager_name, view) in self._views.items():
            manager = self._view_managers[manager_name]
            state = manager.dumper(view)
            views[view_name] = ViewState(manager_name=manager_name, view_state=state)
        window_state = self.saveState().data().decode("utf-8", "ignore")
        window_geometry = self.saveGeometry().data().decode("utf-8", "ignore")
        return WorkSpace(
            views=views,
            docks_state=self._dock_area.saveState(),
            window_state=window_state,
            window_geometry=window_geometry,
        )

    def set_workspace(self, workspace: WorkSpace) -> None:
        views = {}
        for view_name, view_state in workspace.views.items():
            manager_name = view_state.manager_name
            manager = self._view_managers[manager_name]
            view = manager.constructor(view_state.view_state)
            views[view_name] = (manager_name, view)
        self._views = views
        self._dock_area.clear()
        self._add_default_docks()
        for view_name, (manager_name, view) in self._views.items():
            self._add_view(manager_name, view_name, view)
        self._dock_area.restoreState(workspace.docks_state)

    def save_workspace_as(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save current workspace",
            "",
            "JSON (*.json)",
        )
        if file_name:
            workspace = self.get_workspace()
            json_string = serialization.to_json(workspace)
            with open(file_name, "w") as f:
                f.write(json_string)

    def load_workspace(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load workspace",
            "",
            "JSON (*.json)",
        )
        if file_name:
            with open(file_name, "r") as f:
                json_string = f.read()
            workspace = serialization.from_json(json_string, WorkSpace)
            self.set_workspace(workspace)

    def on_sequence_double_clicked(self, path: PureSequencePath) -> None:
        self._sequence_watcher.set_sequence(path)

    def _update_views(self, shot: Shot) -> None:
        for view in self._views.values():
            view[1].display_shot(shot)

    #
    # def add_shots(self, shots: Iterable[Shot]) -> None:
    #     self._shot_selector.add_shots(shots)
    #     self._update_viewers(self._shot_selector.get_selected_shot())
    #
    # def add_view(self, view_type_name: str) -> None:
    #     view_name, ok = QInputDialog().getText(
    #         self, "Choose a name for the view", "Name:"
    #     )
    #     if ok and view_name:
    #         view_type = self._single_shot_viewers[view_type_name]
    #         view = view_type(self._experiment_session_maker)
    #         subwindow = self._mdi_area.addSubWindow(view)
    #         subwindow.setWindowTitle(view_name)
    #         subwindow.show()
    #
    # def reset(self) -> None:
    #     self._shot_selector.reset()
    #
    # def _update_viewers(self, shot) -> None:
    #     for viewer in self._get_viewers().values():
    #         viewer.set_shot(shot)
    #     for viewer in self._get_viewers().values():
    #         viewer.update_view()
    #
    # def _get_viewers(self) -> dict[str, SingleShotView]:
    #     return {
    #         subwindow.windowTitle(): subwindow.widget()
    #         for subwindow in self._mdi_area.subWindowList()
    #     }
    #
    # def load_workspace(self, workspace: "Workspace") -> None:
    #     self.clear()
    #     for name, viewer in workspace.viewers.items():
    #         self.add_view(name, viewer)
    #
    # def extract_workspace(self) -> "Workspace":
    #     viewers = self._get_viewers()
    #     return Workspace(viewers=viewers)
    #
    # def clear(self) -> None:
    #     for subwindow in self._mdi_area.subWindowList():
    #         self._mdi_area.removeSubWindow(subwindow)
    #
    # def on_save_as(self):
    #     directory = platformdirs.user_data_path(
    #         appname="Viewer", appauthor="Caqtus", ensure_exists=True
    #     )
    #     file, _ = QFileDialog.getSaveFileName(
    #         self, "Save Workspace", str(directory), "YAML (*.yaml)"
    #     )
    #     if file:
    #         workspace = self.extract_workspace()
    #         yaml = serialization.converters["yaml"].dumps(workspace, Workspace)
    #         with open(file, "w") as file:
    #             file.write(yaml)
    #
    # def on_load(self):
    #     directory = platformdirs.user_data_path(
    #         appname="Viewer", appauthor="Caqtus", ensure_exists=True
    #     )
    #     file, _ = QFileDialog.getOpenFileName(
    #         self, "Load Workspace", str(directory), "YAML (*.yaml)"
    #     )
    #     if file:
    #         with open(file, "r") as file:
    #             yaml = file.read()
    #         workspace = serialization.converters["yaml"].loads(yaml, Workspace)
    #         self.load_workspace(workspace)


class ShotSelector(QWidget):
    current_shot_changed = Signal(Shot)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setLayout(QHBoxLayout())

        self._shot_spinbox = QSpinBox()
        self._shot_spinbox.setMinimum(0)
        # self._shot_spinbox.valueChanged.connect(self.on_shot_spinbox_value_changed)
        self.layout().addWidget(self._shot_spinbox)

        self._number_shots = 0
        self._current_shot = -1

        self._left_button = QPushButton("<")
        self._left_button.setAutoRepeat(True)
        self._left_button.setAutoRepeatInterval(100)
        # self._left_button.clicked.connect(self.on_left_button_clicked)
        self.layout().addWidget(self._left_button)

        self._pause_button = QPushButton("||")
        # self._pause_button.clicked.connect(self.on_pause_button_clicked)
        self.layout().addWidget(self._pause_button)

        self._right_button = QPushButton(">")
        self._right_button.setAutoRepeat(True)
        self._right_button.setAutoRepeatInterval(100)
        # self._right_button.clicked.connect(self.on_right_button_clicked)
        self.layout().addWidget(self._right_button)

        self._last_button = QPushButton(">>")
        # self._last_button.clicked.connect(self.on_last_button_clicked)
        self.layout().addWidget(self._last_button)
        # noinspection PyUnresolvedReferences
        self.layout().addStretch()
        self._shots: list[Shot] = []

        self.update_spinbox()

    def on_shots_changed(self, shots: collections.abc.Sequence[Shot]) -> None:
        self._number_shots = len(shots)
        self._shots = shots
        if self._current_shot == -1:
            self.current_shot_changed.emit(self._shots[-1])
        self.update_spinbox()

    def on_left_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1

        self._current_shot = max(0, self._current_shot - 1)
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.current_shot_changed.emit(self.get_selected_shot())

    def on_right_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1

        self._current_shot = min(len(self._shots) - 1, self._current_shot + 1)
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.current_shot_changed.emit(self.get_selected_shot())

    def on_last_button_clicked(self) -> None:
        self._current_shot = -1
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.current_shot_changed.emit(self.get_selected_shot())

    def on_pause_button_clicked(self) -> None:
        if self._current_shot == -1:
            self._current_shot = len(self._shots) - 1
        self.update_spinbox()
        # noinspection PyUnresolvedReferences
        self.current_shot_changed.emit(self.get_selected_shot())

    def on_shot_spinbox_value_changed(self, value: int) -> None:
        self._current_shot = value - 1
        # noinspection PyUnresolvedReferences
        self.current_shot_changed.emit(self.get_selected_shot())

    def update_spinbox(self) -> None:
        if self._current_shot == -1:
            current_shot = self._number_shots - 1
        else:
            current_shot = self._current_shot
        with QSignalBlocker(self._shot_spinbox):
            self._shot_spinbox.setMaximum(self._number_shots)
            self._shot_spinbox.setValue(current_shot + 1)
            self._shot_spinbox.setSuffix(f"/{self._number_shots}")
            self._shot_spinbox.setPrefix("Shot: ")


class SequenceWatcher(QObject):
    shots_changed = Signal(list)

    def __init__(self, session_maker: ExperimentSessionMaker):
        super().__init__()
        self._session_maker = session_maker
        self._sequence_path: Optional[PureSequencePath] = None
        self._shots = set[Shot]()
        self._background_scheduler = BackgroundScheduler(on_error="stop_all")

    def __enter__(self):
        self._background_scheduler.__enter__()
        self._background_scheduler.schedule_task(self.update, interval=0.1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._background_scheduler.__exit__(exc_type, exc_val, exc_tb)

    def update(self):
        if self._sequence_path is None:
            return
        with self._session_maker() as session:
            shot_list = unwrap(session.sequences.get_shots(self._sequence_path))
            shots = set(shot_list)
            new_shots = shots - self._shots
            self._shots.update(new_shots)
            if new_shots:
                self.shots_changed.emit(sorted(self._shots, key=lambda shot: shot.index))  # type: ignore

    def set_sequence(self, path: PureSequencePath) -> None:
        self._sequence_path = path
        self._shots.clear()
