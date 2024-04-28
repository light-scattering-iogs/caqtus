from __future__ import annotations

import abc
import asyncio
import datetime
import functools
from typing import Optional, Mapping, assert_never

import attrs
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QWidget,
    QMainWindow,
    QFileDialog,
    QMdiArea,
    QDockWidget,
)

from caqtus.gui.common.sequence_hierarchy import (
    AsyncPathHierarchyView,
)
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    AsyncExperimentSession,
)
from caqtus.session._return_or_raise import unwrap
from caqtus.session.path_hierarchy import PathNotFoundError
from caqtus.session.sequence import Shot
from caqtus.session.sequence_collection import PureShot, PathIsNotSequenceError
from caqtus.utils import serialization
from .main_window_ui import Ui_ShotViewerMainWindow
from .workspace import ViewState, WorkSpace
from ..single_shot_viewers import ShotView, ViewManager, ManagerName


class ShotViewerMainWindow(QMainWindow, Ui_ShotViewerMainWindow):
    def __init__(
        self,
        experiment_session_maker: ExperimentSessionMaker,
        view_managers: Mapping[str, ViewManager],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._views: dict[str, tuple[ManagerName, ShotView]] = {}
        self._experiment_session_maker = experiment_session_maker
        self._view_managers = view_managers
        self._mdi_area = QMdiArea()

        self._hierarchy_view = AsyncPathHierarchyView(
            self._experiment_session_maker, self
        )
        self._setup_ui()
        self.restore_state()
        self._task_group = asyncio.TaskGroup()
        self._state: WidgetState = NoSequenceSelected()

    async def exec_async(self):
        async with self._task_group:
            self._task_group.create_task(self.watch())
            self._task_group.create_task(self._hierarchy_view.run_async())

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
        paths_dock = QDockWidget("Sequences", self)
        paths_dock.setObjectName("SequencesDock")
        paths_dock.setWidget(self._hierarchy_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, paths_dock)

        self.action_save_workspace_as.triggered.connect(self.save_workspace_as)
        self.action_load_workspace.triggered.connect(self.load_workspace)

        self._add_view_managers(self._view_managers)

        self.setWindowTitle("Single Shot Viewer")
        self.setCentralWidget(self._mdi_area)

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
        sub_window = self._mdi_area.addSubWindow(view)
        sub_window.setWindowTitle(view_name)
        sub_window.show()

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
        self._task_group.create_task(self.on_sequence_double_clicked_async(path))

    async def on_sequence_double_clicked_async(self, path: PureSequencePath) -> None:
        async with self._experiment_session_maker.async_session() as session:
            state = await get_state_async(path, session)
            await self._transition(state)

    async def watch(self):
        while True:
            await self.compare()
            await asyncio.sleep(50e-3)

    async def compare(self):
        match self._state:
            case NoSequenceSelected():
                return
            case SequenceSelected(path=path):
                async with self._experiment_session_maker.async_session() as session:
                    new_state = await get_state_async(path, session)
                    if new_state != self._state:
                        await self._transition(new_state)
            case _:
                assert_never(self._state)

    async def _transition(self, state: WidgetState) -> None:
        if isinstance(state, SequenceSelected):
            if state.shots:
                last_shot = max(state.shots, key=lambda s: s.index)
                with self._experiment_session_maker() as session:
                    shot = Shot.bound(last_shot, session)
                    await self._update_views(shot)
        self._state = state

    async def _update_views(self, shot: Shot) -> None:
        async with asyncio.TaskGroup() as tg:
            for view in self._views.values():
                tg.create_task(view[1].display_shot(shot))


@attrs.frozen
class WidgetState(abc.ABC):
    pass


@attrs.frozen
class NoSequenceSelected(WidgetState):
    pass


@attrs.frozen
class SequenceSelected(WidgetState):
    path: PureSequencePath
    start_time: Optional[datetime.datetime]
    shots: frozenset[PureShot]


async def get_state_async(
    sequence_path: Optional[PureSequencePath], session: AsyncExperimentSession
) -> WidgetState:
    if sequence_path is None:
        return NoSequenceSelected()
    shots_result = await session.sequences.get_shots(sequence_path)
    try:
        shots = shots_result.unwrap()
    except (PathNotFoundError, PathIsNotSequenceError):
        return NoSequenceSelected()
    else:
        start_time = unwrap(await session.sequences.get_stats(sequence_path)).start_time
    return SequenceSelected(
        path=sequence_path, shots=frozenset(shots), start_time=start_time
    )

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
