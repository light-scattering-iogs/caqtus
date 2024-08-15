from __future__ import annotations

import abc
import datetime
import functools
from collections.abc import Callable
from typing import Optional, Mapping, assert_never, TypeAlias

import anyio
import attrs
from PySide6.QtCore import QSettings, Qt, QByteArray
from PySide6.QtWidgets import (
    QWidget,
    QMainWindow,
    QFileDialog,
    QMdiArea,
    QDockWidget,
)

from caqtus.gui._common.sequence_hierarchy import AsyncPathHierarchyView
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    AsyncExperimentSession,
)
from caqtus.session import PathNotFoundError, PathIsNotSequenceError, Shot
from caqtus.session._return_or_raise import unwrap
from caqtus.session._sequence_collection import PureShot
from caqtus.utils import serialization
from caqtus.utils.serialization import JSON
from .main_window_ui import Ui_ShotViewerMainWindow
from .workspace import ViewState, WorkSpace
from ..single_shot_viewers import ShotView, ManagerName

ViewCreator: TypeAlias = Callable[[], tuple[str, ShotView]]


class SnapShotWindowHandler:
    def __init__(
        self,
        window: SnapShotMainWindow,
        experiment_session_maker: ExperimentSessionMaker,
    ):
        super().__init__()
        self.window = window
        self.experiment_session_maker = experiment_session_maker
        self.task_group = anyio.create_task_group()
        self.state_lock = anyio.Lock()

        self._state: WidgetState = NoSequenceSelected()
        # Lock to prevent changing the state while comparing if the state is different
        # from the stored sequence.
        self._state_lock = anyio.Lock()

        self.window.hierarchy_view.sequence_double_clicked.connect(
            self.on_sequence_double_clicked
        )

    async def exec_async(self):
        async with self.task_group:
            self.task_group.start_soon(self.watch)
            self.task_group.start_soon(self.window.hierarchy_view.run_async)

    async def watch(self):
        while True:
            await self.update_state()
            await anyio.sleep(50e-3)

    def on_sequence_double_clicked(self, path: PureSequencePath) -> None:
        # We can't transition synchronously now, because the widget might be in the
        # middle of a state comparison or a transition.
        # So instead we schedule the transition to happen asynchronously once it's safe.
        self.task_group.start_soon(self._on_sequence_double_clicked_async, path)

    async def _on_sequence_double_clicked_async(self, path: PureSequencePath) -> None:
        async with (
            self._state_lock,
            self.experiment_session_maker.async_session() as session,
        ):
            state = await get_state_async(path, session)
            await self._transition(state)

    async def update_state(self) -> None:
        """Ensure that the widget displays the up-to-date state of the sequence."""

        async with self._state_lock:
            match self._state:
                case NoSequenceSelected():
                    return
                case SequenceSelected(path=path):
                    async with (
                        self.experiment_session_maker.async_session() as session,
                    ):
                        new_state = await get_state_async(path, session)
                        if new_state != self._state:
                            await self._transition(new_state)
                case _:
                    assert_never(self._state)

    async def _transition(self, state: WidgetState) -> None:
        if isinstance(state, SequenceSelected):
            if state.shots:
                last_shot = max(state.shots, key=lambda s: s.index)
                await self._update_views(last_shot)
        self._state = state

    async def _update_views(self, shot: PureShot) -> None:
        async with anyio.create_task_group() as tg:
            for view in self.window.get_views().values():
                tg.start_soon(self._update_view, shot, view)

    async def _update_view(self, shot: PureShot, view: ShotView) -> None:
        # We need to create a new session for each view, because otherwise the views
        # might use the same session concurrently, which is not allowed.
        with self.experiment_session_maker() as session:
            bound_shot = Shot.bound(shot, session)
            await view.display_shot(bound_shot)


class SnapShotMainWindow(QMainWindow, Ui_ShotViewerMainWindow):
    """The main window of the shot viewer application.

    This window displays the sequences in a dock widget.
    The central widget is a multi-document interface area where the user can open
    multiple views of the shots.
    When a sequence is double-clicked in the sequence dock widget, the window will
    display the last shot of the sequence in all the views.
    """

    def __init__(
        self,
        hierarchy_view: AsyncPathHierarchyView,
        view_creators: Mapping[str, ViewCreator],
        view_dumper: Callable[[ShotView], JSON],
        view_loader: Callable[[JSON], ShotView],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._views: dict[str, tuple[ManagerName, ShotView]] = {}
        self._view_creators = view_creators
        self._mdi_area = QMdiArea()

        self.hierarchy_view = hierarchy_view
        self._setup_ui()
        self.restore_state()

        self._view_dumper = view_dumper
        self._view_loader = view_loader

        self.tile_action.triggered.connect(self._mdi_area.tileSubWindows)

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
        paths_dock.setWidget(self.hierarchy_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, paths_dock)

        self.action_save_workspace_as.triggered.connect(self.save_workspace_as)
        self.action_load_workspace.triggered.connect(self.load_workspace)

        self._add_view_creators(self._view_creators)

        self.setWindowTitle("Single Shot Viewer")
        self.setCentralWidget(self._mdi_area)

    def _add_view_creators(self, view_creators: Mapping[str, ViewCreator]) -> None:
        for name in view_creators:
            self.menu_add_view.addAction(name).triggered.connect(
                functools.partial(self._create_view, name)
            )

    def _create_view(self, creator_name: str) -> None:
        manager = self._view_creators[creator_name]
        name, view = manager()
        self._add_view(name, view)

    def _add_view(self, view_name: str, view: ShotView) -> None:
        sub_window = self._mdi_area.addSubWindow(view)
        sub_window.setWindowTitle(view_name)
        sub_window.show()

    def get_views(self) -> dict[str, ShotView]:
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
                view_state=self._view_dumper(view),
                window_geometry=_bytes_to_str(sub_window.saveGeometry()),
            )
        window_state = _bytes_to_str(self.saveState())
        window_geometry = _bytes_to_str(self.saveGeometry())
        return WorkSpace(
            view_states=view_states,
            window_state=window_state,
            window_geometry=window_geometry,
        )

    def set_workspace(self, workspace: WorkSpace) -> None:
        self.clear()

        self.restoreState(_str_to_bytes_array(workspace.window_state))
        self.restoreGeometry(_str_to_bytes_array(workspace.window_geometry))

        for view_name, view_state in workspace.view_states.items():
            view = self._view_loader(view_state.view_state)
            sub_window = self._mdi_area.addSubWindow(view)
            sub_window.setWindowTitle(view_name)
            sub_window.restoreGeometry(_str_to_bytes_array(view_state.window_geometry))
            sub_window.show()

    def clear(self):
        for sub_window in self._mdi_area.subWindowList():
            sub_window.close()

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


def _str_to_bytes_array(string: str) -> QByteArray:
    return QByteArray.fromHex(bytes(string, "ascii"))


def _bytes_to_str(array: QByteArray) -> str:
    return bytes(array.toHex()).decode("ascii")


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
        shots = unwrap(shots_result)
    except (PathNotFoundError, PathIsNotSequenceError):
        return NoSequenceSelected()
    else:
        start_time = unwrap(await session.sequences.get_stats(sequence_path)).start_time
    return SequenceSelected(
        path=sequence_path, shots=frozenset(shots), start_time=start_time
    )
