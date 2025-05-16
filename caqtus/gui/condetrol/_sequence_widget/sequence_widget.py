from __future__ import annotations

from typing import Optional, Literal, assert_never

import attrs
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QColor, QPalette, QKeySequence, QUndoGroup
from PySide6.QtWidgets import (
    QWidget,
    QToolBar,
    QStackedWidget,
    QLabel,
    QHBoxLayout,
    QApplication,
)
from typing_extensions import assert_type

from caqtus.session import (
    PathNotFoundError,
    SequenceNotEditableError,
    PathIsNotSequenceError,
    State as SequenceState,
    SequenceNotCrashedError,
    SequenceNotLaunchedError,
)
from caqtus.session import (
    PureSequencePath,
    ExperimentSession,
    AsyncExperimentSession,
    TracebackSummary,
)
from caqtus.session._session_maker import StorageManager
from caqtus.types.iteration import IterationConfiguration
from caqtus.types.iteration.steps_configurations import StepsConfiguration
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.timelane import TimeLanes
from caqtus.utils.result import is_failure_type
from .sequence_widget_ui import Ui_SequenceWidget
from .._icons import get_icon
from .._parameter_tables_editor import ParameterNamespaceEditor
from .._sequence_iteration_editors import StepsIterationEditor
from ..timelanes_editor import TimeLanesEditor
from ..timelanes_editor.extension import CondetrolLaneExtensionProtocol
from ..._common.exception_tree import ExceptionDialog

type State = SequenceNotSet | DraftSequence | NotEditableSequence | CrashedSequence

type LiveState = (
    SequenceNotSet | _DraftSequence | _NotEditableSequence | _CrashedSequence
)


@attrs.frozen
class SequenceNotSet:
    pass


@attrs.frozen
class SequenceSetBase:
    """Base class for sequence states that are set.

    Attributes:
        sequence_path: The path of the sequence.
        iterations: The iteration configuration of the sequence.
        time_lanes: The time lanes of the sequence.
        parameters: The global parameters of the sequence.
    """

    sequence_path: PureSequencePath
    iterations: StepsConfiguration
    time_lanes: TimeLanes
    parameters: ParameterNamespace


@attrs.frozen
class DraftSequence(SequenceSetBase):
    """A sequence that is in the draft state."""

    pass


@attrs.frozen
class NotEditableSequence(SequenceSetBase):
    pass


@attrs.frozen
class CrashedSequence(SequenceSetBase):
    traceback: TracebackSummary


@attrs.frozen
class _LiveStateBase:
    parent: SequenceWidget


@attrs.frozen
class _SetSequenceBase(_LiveStateBase):
    sequence_path: PureSequencePath

    def set_fresh_state(self, state: State) -> None:
        self.parent.set_fresh_state(state)

    def get_parameters(self) -> ParameterNamespace:
        return self.parent.parameters_editor.get_parameters()

    def update_global_parameters(self, parameters: ParameterNamespace) -> None:
        self.parent.iteration_editor.set_available_parameter_names(parameters.names())
        self.parent.parameters_editor.set_parameters(parameters)

    def get_iterations(self) -> IterationConfiguration:
        return self.parent.iteration_editor.get_iteration()

    def set_iterations(self, iterations: StepsConfiguration) -> None:
        self.parent.iteration_editor.set_iteration(iterations)

    def get_time_lanes(self) -> TimeLanes:
        return self.parent.time_lanes_editor.get_time_lanes()

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        self.parent.time_lanes_editor.set_time_lanes(time_lanes)


@attrs.frozen
class _DraftSequence(_SetSequenceBase):
    def has_time_lanes_uncommitted_edits(self) -> bool:
        return self.parent.time_lanes_editor.has_uncommitted_edits()

    def time_lanes_edits_committed(self) -> None:
        self.parent.time_lanes_editor.commit_edits()

    def has_iteration_uncommitted_edits(self) -> bool:
        return self.parent.iteration_editor.has_uncommitted_edits()

    def iteration_edits_committed(self) -> None:
        self.parent.iteration_editor.commit_edits()


@attrs.frozen
class _NotEditableSequence(_SetSequenceBase):
    pass


@attrs.frozen
class _CrashedSequence(_SetSequenceBase):
    traceback: TracebackSummary

    def get_traceback(self) -> TracebackSummary:
        return self.traceback

    def set_traceback(self, traceback: TracebackSummary) -> None:
        self.parent._state = _CrashedSequence(
            self.parent, sequence_path=self.sequence_path, traceback=traceback
        )


class SequenceWidget(QWidget, Ui_SequenceWidget):
    """Widget for editing sequence parameters, iterations and time lanes.

    This widget is a tab widget with three tabs: one for defining initial parameters,
    one for editing how the parameters should be iterated over for the sequence, and
    one for editing the time lanes that specify how a given shot should be executed.

    This widget is (optionally) associated with a sequence and displays the iteration
    configuration and time lanes for that sequence.
    If the widget is not associated with a sequence, it will hide itself.

    When associated with a sequence, the widget is constantly watching the state of the
    sequence.
    If the sequence is not in the draft state, the iteration editor and time lanes
    editor
     will become read-only.
    If the sequence is in the draft state, the iteration editor and time lanes editor
    will become editable and any change will be saved.
    """

    sequence_start_requested = Signal(PureSequencePath)
    """A signal emitted when the start sequence button is clicked."""

    def __init__(
        self,
        extension: CondetrolLaneExtensionProtocol,
        parent: Optional[QWidget] = None,
    ):
        """Initializes the sequence widget.

        The sequence widget will initially be associated with no sequence.

        Args:
            extension: The extension that provides time lanes customization.
            parent: The parent widget.
        """

        super().__init__(parent)
        self.setupUi(self)

        self._state: LiveState = SequenceNotSet()
        self.parameters_editor = ParameterNamespaceEditor(self)
        self.parameters_editor.set_read_only(True)
        self.iteration_editor = StepsIterationEditor(self)
        self.time_lanes_editor = TimeLanesEditor(extension, {}, self)
        self.tabWidget.clear()
        self.tabWidget.addTab(self.parameters_editor, "&Constants")
        self.tabWidget.addTab(self.iteration_editor, "&Iteration")
        self.tabWidget.addTab(self.time_lanes_editor, "&Shot")

        # undo
        self.undoView.setCleanIcon(
            get_icon("mdi6.content-save", color=Qt.GlobalColor.gray)
        )
        self.undo_group = QUndoGroup(self)
        self.undo_group.addStack(self.parameters_editor.undo_stack)
        self.undo_group.addStack(self.time_lanes_editor.undo_stack)
        self.undo_group.addStack(self.iteration_editor.undo_stack)
        self.tabWidget.currentChanged.connect(self._on_tab_changed)
        self.undo_group.setActiveStack(self.time_lanes_editor.undo_stack)
        self.undoView.setGroup(self.undo_group)
        self.undoView.setVisible(False)

        self.tool_bar = QToolBar(self)
        self.status_widget = IconLabel(icon_position="left")
        self.warning_action = self.tool_bar.addAction(
            get_icon("mdi6.alert", color=QColor(205, 22, 17)), "warning"
        )
        self.warning_action.triggered.connect(self._on_warning_action_triggered)
        self.warning_action.setToolTip("Error")

        self.tool_bar.addWidget(self.status_widget)
        self.start_sequence_action = self.tool_bar.addAction(
            get_icon("start", color=Qt.GlobalColor.darkGreen), "start"
        )
        self.start_sequence_action.triggered.connect(self._on_start_sequence_requested)
        self.start_sequence_action.setShortcut(QKeySequence("F5"))
        self.tool_bar.addSeparator()
        undo_action = self.undo_group.createUndoAction(self)
        undo_icon = get_icon("mdi6.undo")
        undo_action.setIcon(undo_icon)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self.tool_bar.addAction(undo_action)
        redo_action = self.undo_group.createRedoAction(self)
        redo_icon = get_icon("mdi6.redo")
        redo_action.setIcon(redo_icon)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        self.tool_bar.addAction(redo_action)

        self.verticalLayout.insertWidget(0, self.tool_bar)
        self.stacked = QStackedWidget(self)
        self.stacked.addWidget(QWidget(self))
        self.stacked.addWidget(self.iteration_editor.toolbar)
        self.stacked.addWidget(self.time_lanes_editor.toolbar)
        self.stacked.setCurrentIndex(0)
        self.tool_bar.addSeparator()
        self.tool_bar.addWidget(self.stacked)

        self.tabWidget.currentChanged.connect(self.stacked.setCurrentIndex)

        self._exception_dialog = ExceptionDialog(self)
        self.set_fresh_state(SequenceNotSet())

    def _on_tab_changed(self, index: int) -> None:
        stacks = [
            self.parameters_editor.undo_stack,
            self.iteration_editor.undo_stack,
            self.time_lanes_editor.undo_stack,
        ]
        self.undo_group.setActiveStack(stacks[index])

    def set_fresh_state(self, state: State) -> None:
        match state:
            case SequenceNotSet():
                self.setEnabled(False)
                self.setVisible(False)
                self.start_sequence_action.setEnabled(False)
                new_state = SequenceNotSet()
            case (
                DraftSequence() | NotEditableSequence() | CrashedSequence() as set_state
            ):
                self.iteration_editor.set_iteration(set_state.iterations)
                self.time_lanes_editor.set_time_lanes(set_state.time_lanes)
                self.parameters_editor.set_parameters(set_state.parameters)
                path = set_state.sequence_path
                self.setEnabled(True)
                self.setVisible(True)
                match set_state:
                    case DraftSequence():
                        self.start_sequence_action.setEnabled(True)
                        self.time_lanes_editor.set_read_only(False)
                        self.iteration_editor.set_read_only(False)
                        self.warning_action.setVisible(False)
                        self._set_status_widget(path, True)
                        new_state = _DraftSequence(self, sequence_path=path)
                    case NotEditableSequence():
                        self.start_sequence_action.setEnabled(False)
                        self.time_lanes_editor.set_read_only(True)
                        self.iteration_editor.set_read_only(True)
                        self.warning_action.setVisible(False)
                        self._set_status_widget(path, False)
                        new_state = _NotEditableSequence(self, sequence_path=path)
                    case CrashedSequence(traceback=tb):
                        self.start_sequence_action.setEnabled(False)
                        self.time_lanes_editor.set_read_only(True)
                        self.iteration_editor.set_read_only(True)
                        self.warning_action.setVisible(True)
                        self._set_status_widget(path, False)
                        new_state = _CrashedSequence(
                            self, sequence_path=path, traceback=tb
                        )
                    case _:
                        assert_never(set_state)
            case _:
                assert_never(state)
        self._state = new_state

    def get_current_state(self) -> LiveState:
        return self._state

    def _on_warning_action_triggered(self) -> None:
        """Display the sequence traceback in a dialog."""

        assert isinstance(self._state, _CrashedSequence)

        color = QApplication.palette().color(QPalette.ColorRole.Accent).name()
        self._exception_dialog.set_message(
            f"An error occurred while running the sequence "
            f"<b><font color='{color}'>{self._state.sequence_path}</font></b>."
        )
        traceback = self._state.traceback
        self._exception_dialog.set_exception(traceback)
        self._exception_dialog.show()

    def _set_status_widget(self, path: PureSequencePath, editable: bool) -> None:
        text = " > ".join(path.parts)
        color = self.palette().text().color()
        if editable:
            icon = get_icon("editable-sequence", color=color)
        else:
            icon = get_icon("read-only-sequence", color=color)
        self.status_widget.set_text(text)
        self.status_widget.set_icon(icon)

    def _on_start_sequence_requested(self):
        assert isinstance(self._state, _DraftSequence)
        self.sequence_start_requested.emit(self._state.sequence_path)


async def synchronize_sequence_widget(
    widget: SequenceWidget, storage_manager: StorageManager
) -> None:
    async with storage_manager.async_session() as session:
        await synchronize_editor_and_storage(widget, session)


async def synchronize_editor_and_storage(
    editor: SequenceWidget, session: AsyncExperimentSession
) -> bool:
    """Synchronize what is displayed in the editor with the session storage.

    Returns:
        True if there was some difference between the editor and the storage, and
        the changes were resolved.
        False otherwise.
    """

    editor_state = editor.get_current_state()
    match editor_state:
        case SequenceNotSet():
            return False
        case (
            _DraftSequence(sequence_path=path)
            | _NotEditableSequence(sequence_path=path)
            | _CrashedSequence(sequence_path=path)
        ):
            storage_state = await _query_state_async(path, session)
            if editor_state != editor.get_current_state():
                # Could be that the editor state changed while fetching the data from
                # the storage.
                # In this case we relaunch the synchronization.
                return await synchronize_editor_and_storage(editor, session)
            else:
                if isinstance(storage_state, SequenceNotSet):
                    editor.set_fresh_state(storage_state)
                    return True
                return await synchronize_editor_and_storage_sequence_data(
                    editor_state, session, storage_state
                )

        case _:
            assert_never(editor_state)


async def synchronize_editor_and_storage_sequence_data(
    editor_state: _DraftSequence | _NotEditableSequence | _CrashedSequence,
    session: AsyncExperimentSession,
    storage_state: DraftSequence | NotEditableSequence | CrashedSequence,
) -> bool:
    match editor_state:
        case _DraftSequence() as editor_state:
            return await synchronize_draft_sequence(
                editor_state, session, storage_state
            )
        case _NotEditableSequence() as editor_state:
            return await synchronize_not_editable_sequence(editor_state, storage_state)
        case _CrashedSequence() as editor_state:
            return await synchronize_crashed_sequence(editor_state, storage_state)
        case _:
            assert_never(editor_state)


async def synchronize_draft_sequence(
    editor_state: _DraftSequence, session: AsyncExperimentSession, state: State
) -> bool:
    match state:
        case SequenceNotSet() | NotEditableSequence() | CrashedSequence():
            editor_state.set_fresh_state(state)
            return True
        case DraftSequence():
            changes = False

            if editor_state.get_parameters() != state.parameters:
                editor_state.update_global_parameters(state.parameters)
                changes = True

            if editor_state.has_iteration_uncommitted_edits():
                iterations = editor_state.get_iterations()
                editor_state.iteration_edits_committed()
                result = await session.sequences.set_iteration_configuration(
                    editor_state.sequence_path, iterations
                )
                assert not is_failure_type(
                    result,
                    (
                        PathNotFoundError,
                        PathIsNotSequenceError,
                        SequenceNotEditableError,
                    ),
                ), "Path should exists in the session and be an editable sequence."
                assert_type(result, None)
                changes = True
            elif editor_state.get_iterations() != state.iterations:
                editor_state.set_iterations(state.iterations)
                changes = True

            editor_time_lanes = editor_state.get_time_lanes()
            if editor_state.has_time_lanes_uncommitted_edits():
                editor_state.time_lanes_edits_committed()
                result = await session.sequences.set_time_lanes(
                    editor_state.sequence_path, editor_time_lanes
                )
                assert not is_failure_type(
                    result,
                    (
                        PathNotFoundError,
                        PathIsNotSequenceError,
                        SequenceNotEditableError,
                    ),
                ), "Path should exists in the session and be an editable sequence."
                assert_type(result, None)
                changes = True
            elif editor_time_lanes != state.time_lanes:
                editor_state.set_time_lanes(state.time_lanes)
                changes = True
            return changes
        case _:
            assert_never(state)


async def synchronize_not_editable_sequence(
    editor_state: _NotEditableSequence, state: State
) -> bool:
    match state:
        case SequenceNotSet() | DraftSequence() | CrashedSequence():
            editor_state.set_fresh_state(state)
            return True
        case NotEditableSequence():
            changes = False
            if editor_state.get_parameters() != state.parameters:
                editor_state.update_global_parameters(state.parameters)
                changes = True

            if editor_state.get_iterations() != state.iterations:
                editor_state.set_iterations(state.iterations)
                changes = True

            if editor_state.get_time_lanes() != state.time_lanes:
                editor_state.set_time_lanes(state.time_lanes)
                changes = True
            return changes
        case _:
            assert_never(state)


async def synchronize_crashed_sequence(
    editor_state: _CrashedSequence, state: State
) -> bool:
    match state:
        case SequenceNotSet() | DraftSequence() | NotEditableSequence():
            editor_state.set_fresh_state(state)
            return True
        case CrashedSequence():
            changes = False
            if editor_state.get_parameters() != state.parameters:
                editor_state.update_global_parameters(state.parameters)
                changes = True

            if editor_state.get_iterations() != state.iterations:
                editor_state.set_iterations(state.iterations)
                changes = True

            if editor_state.get_time_lanes() != state.time_lanes:
                editor_state.set_time_lanes(state.time_lanes)
                changes = True

            if editor_state.get_traceback() != state.traceback:
                editor_state.set_traceback(state.traceback)
                changes = True
            return changes
        case _:
            assert_never(state)


def _query_state_sync(path: PureSequencePath, session: ExperimentSession) -> State:
    is_sequence_result = session.sequences.is_sequence(path)
    if is_failure_type(is_sequence_result, PathNotFoundError):
        return SequenceNotSet()
    else:
        if is_sequence_result.result():
            return _query_sequence_state_sync(path, session)
        else:
            return SequenceNotSet()


def _query_sequence_state_sync(
    path: PureSequencePath, session: ExperimentSession
) -> DraftSequence | NotEditableSequence | CrashedSequence:
    state_result = session.sequences.get_state(path)
    assert not is_failure_type(
        state_result, (PathNotFoundError, PathIsNotSequenceError)
    ), "Path should exists in the session and be a sequence."
    state = state_result.content()
    iterations = session.sequences.get_iteration_configuration(path)
    if not isinstance(iterations, StepsConfiguration):
        raise NotImplementedError("Only steps iterations are supported.")
    time_lanes = session.sequences.get_time_lanes(path)
    assert not is_failure_type(
        time_lanes, (PathNotFoundError, PathIsNotSequenceError)
    ), "Path should exists in the session and be a sequence."

    if state.is_editable():
        parameters = session.get_global_parameters()
        return DraftSequence(
            path, iterations=iterations, time_lanes=time_lanes, parameters=parameters
        )
    else:
        parameters_result = session.sequences.get_global_parameters(path)
        assert not is_failure_type(
            parameters_result,
            (PathNotFoundError, PathIsNotSequenceError, SequenceNotLaunchedError),
        ), "Path should exists in the session and be a launched sequence."
        parameters = parameters_result.content()
        if state == SequenceState.CRASHED:
            traceback_summary_result = session.sequences.get_exception(path)
            assert not is_failure_type(
                traceback_summary_result,
                (PathNotFoundError, PathIsNotSequenceError, SequenceNotCrashedError),
            ), "Path should exists in the session and be a crashed sequence."
            traceback_summary = traceback_summary_result.content()
            if traceback_summary is None:
                error = RuntimeError("Sequence crashed but no traceback available.")
                traceback_summary = TracebackSummary.from_exception(error)
            return CrashedSequence(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
                traceback=traceback_summary,
            )
        else:
            return NotEditableSequence(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
            )


async def _query_state_async(
    path: PureSequencePath, session: AsyncExperimentSession
) -> State:
    is_sequence_result = await session.sequences.is_sequence(path)
    if is_failure_type(is_sequence_result, PathNotFoundError):
        return SequenceNotSet()
    else:
        if is_sequence_result.result():
            return await _query_sequence_state_async(path, session)
        else:
            return SequenceNotSet()


async def _query_sequence_state_async(
    path: PureSequencePath, session: AsyncExperimentSession
) -> DraftSequence | NotEditableSequence | CrashedSequence:
    state_result = await session.sequences.get_state(path)
    assert not is_failure_type(
        state_result, (PathNotFoundError, PathIsNotSequenceError)
    ), "Path should exists in the session and be a sequence."
    state = state_result.content()
    iterations = await session.sequences.get_iteration_configuration(path)
    if not isinstance(iterations, StepsConfiguration):
        raise NotImplementedError("Only steps iterations are supported.")
    time_lanes = await session.sequences.get_time_lanes(path)
    assert not is_failure_type(
        time_lanes, (PathNotFoundError, PathIsNotSequenceError)
    ), "Path should exists in the session and be a sequence."

    if state.is_editable():
        parameters = await session.get_global_parameters()
        return DraftSequence(
            path, iterations=iterations, time_lanes=time_lanes, parameters=parameters
        )
    else:
        parameters_result = await session.sequences.get_global_parameters(path)
        assert not is_failure_type(
            parameters_result,
            (PathNotFoundError, PathIsNotSequenceError, SequenceNotLaunchedError),
        ), "Path should exists in the session and be a launched sequence."
        parameters = parameters_result.content()
        if state == SequenceState.CRASHED:
            traceback_summary_result = await session.sequences.get_traceback_summary(
                path
            )
            assert not is_failure_type(
                traceback_summary_result,
                (PathNotFoundError, PathIsNotSequenceError, SequenceNotCrashedError),
            ), "Path should exists in the session and be a crashed sequence."
            traceback_summary = traceback_summary_result.content()
            if traceback_summary is None:
                error = RuntimeError("Sequence crashed but no traceback available.")
                traceback_summary = TracebackSummary.from_exception(error)
            return CrashedSequence(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
                traceback=traceback_summary,
            )
        else:
            return NotEditableSequence(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
            )


class IconLabel(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon_position: Literal["left", "right"] = "left",
    ):
        super().__init__(parent)
        self._label = QLabel()
        self._icon = QLabel()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if icon_position == "left":
            layout.addWidget(self._icon)
            layout.addWidget(self._label)
        else:
            layout.addWidget(self._label)
            layout.addWidget(self._icon)
        self.setLayout(layout)

    def set_text(self, text: str):
        self._label.setText(text)

    def set_icon(self, icon: Optional[QIcon]):
        if icon is None:
            self._icon.clear()
        else:
            self._icon.setPixmap(icon.pixmap(20, 20))
