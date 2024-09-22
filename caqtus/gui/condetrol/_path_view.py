from __future__ import annotations

import functools
from typing import assert_never, Optional

import anyio
import anyio.abc
import anyio.lowlevel
from PySide6 import QtCore
from PySide6.QtCore import (
    QModelIndex,
)
from PySide6.QtWidgets import (
    QMenu,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QApplication,
    QAbstractItemView,
)

from caqtus.gui._common.sequence_hierarchy import (
    AsyncPathHierarchyView,
)
from caqtus.gui.qtutil import temporary_widget
from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    PathIsRootError,
    PathNotFoundError,
)
from caqtus.session import (
    PathIsSequenceError,
    PathHasChildrenError,
    State,
)
from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    ArangeLoop,
    ExecuteShot,
)
from caqtus.types.timelane import TimeLanes
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils._result import Failure, is_success, is_failure_type
from ._icons import get_icon
from .._common.waiting_widget import blocking_call


class EditablePathHierarchyView(AsyncPathHierarchyView):
    sequence_start_requested = QtCore.Signal(PureSequencePath)
    sequence_interrupt_requested = QtCore.Signal(PureSequencePath)

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        parent=None,
    ):
        super().__init__(session_maker, parent)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)  # type: ignore
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._task_group: Optional[anyio.abc.TaskGroup] = None

    async def run_async(self) -> None:
        async with anyio.create_task_group() as self._task_group:
            await super().run_async()

    def show_context_menu(self, pos):
        proxy_index = self.indexAt(pos)
        index = self._proxy_model.mapToSource(proxy_index)

        path = self._model.get_path(index)

        with temporary_widget(QMenu(self)) as menu:
            color = self.palette().text().color()

            with self.session_maker() as session:
                is_sequence = session.sequences.is_sequence(path).unwrap()
                if is_sequence:
                    state = session.sequences.get_state(path).unwrap()
                else:
                    state = None

            if not is_sequence:
                new_menu = menu.addMenu("New...")

                create_folder_action = new_menu.addAction("folder")
                create_folder_action.triggered.connect(
                    functools.partial(self.create_new_folder, path)
                )

                create_sequence_action = new_menu.addAction("sequence")
                create_sequence_action.triggered.connect(
                    functools.partial(self.create_new_sequence, index)
                )
            if is_sequence:
                play_icon = get_icon("start", color)
                start_action = menu.addAction(play_icon, "Start")
                if state == State.DRAFT:
                    start_action.setEnabled(True)
                else:
                    start_action.setEnabled(False)
                start_action.triggered.connect(
                    lambda: self.sequence_start_requested.emit(path)
                )

                stop_icon = get_icon("stop", color)
                stop_action = menu.addAction(stop_icon, "Interrupt")
                if state == State.RUNNING:
                    stop_action.setEnabled(True)
                else:
                    stop_action.setEnabled(False)
                stop_action.triggered.connect(
                    lambda: self.sequence_interrupt_requested.emit(path)
                )

                duplicate_icon = get_icon("duplicate", color)
                duplicate_action = menu.addAction(duplicate_icon, "Duplicate")
                duplicate_action.triggered.connect(
                    functools.partial(self.on_sequence_duplication_requested, index)
                )

                clear_icon = get_icon("clear", color)
                clear_action = menu.addAction(clear_icon, "Clear")
                clear_action.triggered.connect(
                    functools.partial(self.on_clear_sequence_requested, path)
                )
                if state not in {
                    State.FINISHED,
                    State.INTERRUPTED,
                    State.CRASHED,
                }:
                    clear_action.setEnabled(False)

            if not path.is_root():
                trash_icon = get_icon("delete", color)
                delete_action = menu.addAction(trash_icon, "Delete")
                if state not in {
                    State.DRAFT,
                    State.FINISHED,
                    State.INTERRUPTED,
                    State.CRASHED,
                    None,
                }:
                    delete_action.setEnabled(False)
                delete_action.triggered.connect(functools.partial(self.delete, index))
            if index.isValid():
                rename_action = menu.addAction(
                    get_icon("mdi6.form-textbox", color), "Rename"
                )
                rename_action.triggered.connect(
                    functools.partial(self.on_rename_requested, index)
                )

            menu.exec(self.mapToGlobal(pos))

    def on_rename_requested(self, index: QModelIndex) -> None:
        """Ask the user for a new name and rename the sequence."""

        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance")

        path = self._model.get_path(index)

        assert path.name is not None

        text, ok = QInputDialog().getText(
            self,
            f"Rename {path}...",
            "New name:",
            QLineEdit.EchoMode.Normal,
            path.name,
        )
        if ok and text:
            if PureSequencePath.is_valid_name(text):
                result = self._model.rename(index, text)
                if isinstance(result, Failure):
                    QMessageBox.warning(
                        self,
                        app.applicationName(),
                        f"<p>Could not rename <i>{path.name}</i> to "
                        f"<i>{text}</i>:</p>"
                        f"<p>{result.error}</p>",
                    )
            else:
                QMessageBox.warning(
                    self,
                    app.applicationName(),
                    f"Name <i>{text}</i> is not valid.",
                )
                self.on_rename_requested(index)

    def on_clear_sequence_requested(self, path: PureSequencePath) -> None:
        """Clear the sequence at the given path.

        This will revert the sequence to the draft state, effectively clearing all
        the data in it.
        During the process, a waiting widget will be shown to the user to prevent them
        from interacting with the sequence while it is being cleared.
        """

        async def clear():
            async with self.session_maker.async_session() as session:
                await session.sequences.set_state(path, State.DRAFT)
                await anyio.lowlevel.checkpoint()

        if self._task_group is None:
            raise RuntimeError("Task group not initialized")

        self._task_group.start_soon(
            blocking_call,
            self,
            f"<p>Clearing <b><i>{path}</i></b></p><p>This may take a while...</p>",
            clear,
        )

    def on_sequence_duplication_requested(self, source: QModelIndex):
        """Ask the user for a new sequence name and duplicate the sequence."""

        path = self._model.get_path(source)

        assert path.name is not None

        text, ok = QInputDialog().getText(
            self,
            f"Duplicate {path}...",
            "New sequence name:",
            QLineEdit.EchoMode.Normal,
            path.name,
        )
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance")
        title = app.applicationName()
        if ok and text:
            with self.session_maker() as session:
                iterations = session.sequences.get_iteration_configuration(path)
                time_lanes = session.sequences.get_time_lanes(path)
            if text.startswith(PureSequencePath._separator()):
                if not PureSequencePath.is_valid_path(text):
                    QMessageBox.warning(
                        self,
                        title,
                        f"Path '{text}' is not valid for a sequence.",
                    )
                    return
                path = PureSequencePath(text)
                with self.session_maker() as session:
                    creation_result = session.sequences.create(
                        path, iterations, time_lanes
                    )
            else:
                if not PureSequencePath.is_valid_name(text):
                    QMessageBox.warning(
                        self,
                        title,
                        f"Name '{text}' is not valid for a sequence.",
                    )
                    return
                creation_result = self._model.create_new_sequence(
                    source.parent(), text, iterations, time_lanes
                )
            try:
                creation_result.unwrap()
            except PathIsSequenceError:
                QMessageBox.warning(
                    self,
                    title,
                    f"Target <i>{text}</i> already exists and is a sequence.",
                )
            except PathHasChildrenError:
                QMessageBox.warning(
                    self,
                    title,
                    f"Target <i>{text}</i> already exists and has children.",
                )

    def create_new_folder(self, path: PureSequencePath):
        text, ok = QInputDialog().getText(
            self,
            f"New folder in {path}...",
            "Folder name:",
            QLineEdit.EchoMode.Normal,
            "new folder",
        )
        if ok and text:
            new_path = path / text
            with self.session_maker() as session:
                session.paths.create_path(new_path)

    def create_new_sequence(self, parent: QModelIndex):
        path = self._model.get_path(parent)
        text, ok = QInputDialog().getText(
            self,
            f"New sequence in {path}...",
            "Sequence name:",
            QLineEdit.EchoMode.Normal,
            "new sequence",
        )
        if ok and text:
            self._model.create_new_sequence(
                parent, text, DEFAULT_ITERATION_CONFIG, DEFAULT_TIME_LANES
            )

    def delete(self, index: QModelIndex):
        path = self._model.get_path(index)
        message = (
            f'You are about to delete "{path}".\n'
            "All data inside will be irremediably lost."
        )
        if self.exec_confirmation_message_box(message):
            result = self._model.remove_path(index)

            assert not is_failure_type(result, PathIsRootError)

            if is_success(result):
                return
            if is_failure_type(result, PathNotFoundError):
                return  # The path was already deleted
            if is_failure_type(result, PathIsSequenceError):
                app = QApplication.instance()
                if app is None:
                    raise RuntimeError("No QApplication instance")
                QMessageBox.warning(
                    self,
                    app.applicationName(),
                    f"The path '{path}' contains sequences and therefore "
                    f"cannot be deleted",
                )
                return
            assert_never(result)

    def exec_confirmation_message_box(self, message: str) -> bool:
        """Show a popup box to ask  a question."""

        with temporary_widget(QMessageBox(self)) as message_box:
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("No QApplication instance")
            message_box.setWindowTitle(app.applicationName())
            message_box.setText(message)
            message_box.setInformativeText("Are you really sure you want to continue?")
            message_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            message_box.setIcon(QMessageBox.Icon.Warning)
            result = message_box.exec()
            if result == QMessageBox.StandardButton.Cancel:
                return False
            return True


DEFAULT_ITERATION_CONFIG = StepsConfiguration(
    steps=[
        ArangeLoop(
            variable=DottedVariableName("rep"),
            start=Expression("0"),
            stop=Expression("10"),
            step=Expression("1"),
            sub_steps=[ExecuteShot()],
        ),
    ]
)

DEFAULT_TIME_LANES = TimeLanes(
    step_names=["step 0"],
    step_durations=[Expression("...")],
    lanes={},
)
