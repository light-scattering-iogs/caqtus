from __future__ import annotations

from typing import Optional, Literal, assert_never

import anyio
import attrs
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QColor, QPalette, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QToolBar,
    QStackedWidget,
    QLabel,
    QHBoxLayout,
    QApplication,
)

from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    ExperimentSession,
    AsyncExperimentSession,
    TracebackSummary,
)
from caqtus.session import (
    PathNotFoundError,
    SequenceNotEditableError,
    PathIsNotSequenceError,
    State,
)
from caqtus.types.iteration import IterationConfiguration
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.timelane import TimeLanes
from caqtus.utils.result import is_failure_type
from caqtus.utils.result import unwrap
from .sequence_widget_ui import Ui_SequenceWidget
from .._icons import get_icon
from .._parameter_tables_editor import ParameterNamespaceEditor
from .._sequence_iteration_editors import StepsIterationEditor
from ..timelanes_editor import TimeLanesEditor
from ..timelanes_editor.extension import CondetrolLaneExtensionProtocol
from ..._common.exception_tree import ExceptionDialog

type State = SequenceNotSet | DraftSequence | FinishedSequence | CrashedSequence

type LiveState = SequenceNotSet | _DraftSequence | _FinishedSequence | _CrashedSequence


@attrs.frozen
class SequenceNotSet:
    pass


@attrs.frozen
class SequenceSetBase:
    sequence_path: PureSequencePath
    iterations: IterationConfiguration
    time_lanes: TimeLanes
    parameters: ParameterNamespace


@attrs.frozen
class DraftSequence(SequenceSetBase):
    pass


@attrs.frozen
class FinishedSequence(SequenceSetBase):
    pass


@attrs.frozen
class CrashedSequence(SequenceSetBase):
    traceback: TracebackSummary


@attrs.define
class _LiveStateBase:
    parent: SequenceWidget


@attrs.define
class _SetSequenceBase(_LiveStateBase):
    sequence_path: PureSequencePath

    def update_global_parameters(self, parameters: ParameterNamespace) -> None:
        self.parent.iteration_editor.set_available_parameter_names(parameters.names())
        self.parent.parameters_editor.set_parameters(parameters)


@attrs.frozen
class _DraftSequence(_SetSequenceBase):
    pass


@attrs.frozen
class _FinishedSequence(_SetSequenceBase):
    pass


@attrs.frozen
class _CrashedSequence(_SetSequenceBase):
    traceback: TracebackSummary


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
        self.time_lanes_editor = TimeLanesEditor(extension, {}, self)
        self.iteration_editor = StepsIterationEditor(self)

        self.tabWidget.clear()
        self.tabWidget.addTab(self.parameters_editor, "&Globals")
        self.tabWidget.addTab(self.iteration_editor, "&Parameters")
        self.tabWidget.addTab(self.time_lanes_editor, "Time &lanes")

        self.parameters_editor.set_read_only(True)

        self.setup_connections()

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

    def set_fresh_state(self, state: State) -> None:
        match state:
            case SequenceNotSet():
                self.setEnabled(False)
                self.start_sequence_action.setEnabled(False)
                new_state = SequenceNotSet()
            case SequenceSetBase(
                sequence_path=path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
            ) as set_state:
                self.iteration_editor.set_iteration(iterations)
                self.time_lanes_editor.set_time_lanes(time_lanes)
                self.parameters_editor.set_parameters(parameters)
                self.setEnabled(True)
                match set_state:
                    case DraftSequence():
                        self.start_sequence_action.setEnabled(True)
                        self.time_lanes_editor.set_read_only(False)
                        self.iteration_editor.set_read_only(False)
                        self.warning_action.setVisible(False)
                        self._set_status_widget(path, True)
                        new_state = _DraftSequence(self, sequence_path=path)
                    case FinishedSequence():
                        self.start_sequence_action.setEnabled(False)
                        self.time_lanes_editor.set_read_only(True)
                        self.iteration_editor.set_read_only(True)
                        self.warning_action.setVisible(False)
                        self._set_status_widget(path, False)
                        new_state = _FinishedSequence(self, sequence_path=path)
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

    async def exec_async(self) -> None:
        while True:
            await self.watch_sequence()
            await anyio.sleep(10e-3)

    async def watch_sequence(self) -> None:
        if isinstance(self._state, _SequenceNotSetState):
            return
        elif isinstance(self._state, _SequenceSetState):
            old_state = self._state
            new_state = await _query_state_async(
                self._state.sequence_path, self.session_maker
            )
            # It could be that the widget state changed while we were fetching infos,
            # for example if set_sequence is called or the editors emitted editions.
            if old_state != self._state:
                return

            if new_state != self._state:
                self._transition(new_state)
        else:
            raise AssertionError("Invalid state")

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

    def setup_connections(self):
        self.time_lanes_editor.time_lanes_edited.connect(self.on_time_lanes_edited)
        self.iteration_editor.iteration_edited.connect(
            self.on_sequence_iteration_edited
        )

    def on_sequence_iteration_edited(self, iterations: IterationConfiguration):
        assert isinstance(self._state, _SequenceEditableState)
        with self.session_maker() as session:
            try:
                session.sequences.set_iteration_configuration(
                    self._state.sequence_path, iterations
                )
            except (PathNotFoundError, PathIsNotSequenceError):
                self._transition(_SequenceNotSetState())
            except SequenceNotEditableError:
                self._transition(
                    _query_state_sync(self._state.sequence_path, self.session_maker)
                )
            else:
                self._state = attrs.evolve(self._state, iterations=iterations)

    def on_time_lanes_edited(self, time_lanes: TimeLanes):
        assert isinstance(self._state, _SequenceEditableState)
        with self.session_maker() as session:
            try:
                session.sequences.set_time_lanes(self._state.sequence_path, time_lanes)
            except (PathNotFoundError, PathIsNotSequenceError):
                self._transition(_SequenceNotSetState())
            except SequenceNotEditableError:
                self._transition(
                    _query_state_sync(self._state.sequence_path, self.session_maker)
                )
            else:
                self._state = attrs.evolve(self._state, time_lanes=time_lanes)


async def _query_state_async(
    path: PureSequencePath, session_maker: ExperimentSessionMaker
) -> _State:
    async with session_maker.async_session() as session:
        is_sequence_result = await session.sequences.is_sequence(path)
        if is_failure_type(is_sequence_result, PathNotFoundError):
            return _SequenceNotSetState()
        else:
            if is_sequence_result.result():
                return await _query_sequence_state_async(path, session)
            else:
                return _SequenceNotSetState()


async def _query_sequence_state_async(
    path: PureSequencePath, session: AsyncExperimentSession
) -> _SequenceSetState:
    # These results can be unwrapped safely because we checked that the sequence
    # exists in the session.
    state = unwrap(await session.sequences.get_state(path))
    iterations = await session.sequences.get_iteration_configuration(path)
    time_lanes = await session.sequences.get_time_lanes(path)

    if state.is_editable():
        return _SequenceEditableState(
            path, iterations=iterations, time_lanes=time_lanes, sequence_state=state
        )
    else:
        parameters = unwrap(await session.sequences.get_global_parameters(path))
        if state == State.CRASHED:
            tb_summary = unwrap(await session.sequences.get_traceback_summary(path))
            return _SequenceCrashedState(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
                sequence_state=state,
                exception_traceback=tb_summary,
            )
        else:
            return _SequenceNotEditableState(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
                sequence_state=state,
            )


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
) -> DraftSequence | FinishedSequence | CrashedSequence:
    # These results can be unwrapped safely because we checked that the sequence
    # exists in the session.
    state = unwrap(session.sequences.get_state(path))
    iterations = session.sequences.get_iteration_configuration(path)
    time_lanes = session.sequences.get_time_lanes(path)

    if state.is_editable():
        parameters = session.get_global_parameters()
        return DraftSequence(
            path, iterations=iterations, time_lanes=time_lanes, parameters=parameters
        )
    else:
        parameters = unwrap(session.sequences.get_global_parameters(path))
        if state == State.CRASHED:
            traceback_summary = unwrap(session.sequences.get_exception(path))
            return CrashedSequence(
                path,
                iterations=iterations,
                time_lanes=time_lanes,
                parameters=parameters,
                traceback=traceback_summary,
            )
        else:
            return FinishedSequence(
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
