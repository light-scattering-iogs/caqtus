from __future__ import annotations

import abc
import asyncio
import datetime
import functools
from typing import Optional, Mapping, assert_never

import attrs
from PySide6.QtCore import QSettings, Qt, QByteArray
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


def _bytes_to_str(array: QByteArray) -> str:
    return array.data().decode("utf-8", "ignore")


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
                self._add_view(view_name, view)
            case _:
                assert_never(created)

    def _add_view(self, view_name: str, view: ShotView) -> None:
        sub_window = self._mdi_area.addSubWindow(view)
        sub_window.setWindowTitle(view_name)
        sub_window.show()

    def _get_views(self) -> dict[str, ShotView]:
        return {
            sub_window.windowTitle(): sub_window.widget()
            for sub_window in self._mdi_area.subWindowList()
        }

    def get_workspace(self) -> WorkSpace:
        view_states = {}
        for sub_window in self._mdi_area.subWindowList():
            view_name = sub_window.windowTitle()
            view = sub_window.widget()
            assert isinstance(view, ShotView)
            view_states[view_name] = ViewState(
                view_state=view.get_state(),
                window_geometry=_bytes_to_str(sub_window.saveGeometry()),
                window_state=_bytes_to_str(sub_window.saveState()),
            )
        window_state = _bytes_to_str(self.saveState())
        window_geometry = _bytes_to_str(self.saveGeometry())
        return WorkSpace(
            view_states=view_states,
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
            for view in self._get_views().values():
                tg.create_task(view.display_shot(shot))


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
