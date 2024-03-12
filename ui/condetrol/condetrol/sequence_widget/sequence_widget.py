from __future__ import annotations

from typing import Optional

import attrs
from PySide6.QtCore import QThread, QTimer, Signal, QEvent
from PySide6.QtStateMachine import QStateMachine, QState
from PySide6.QtWidgets import QWidget
from core.session import ExperimentSessionMaker, PureSequencePath, ParameterNamespace
from core.session._return_or_raise import unwrap
from core.session.path_hierarchy import PathNotFoundError
from core.session.sequence import State, Sequence
from core.session.sequence.iteration_configuration import (
    IterationConfiguration,
    StepsConfiguration,
)
from core.session.sequence_collection import (
    PathIsNotSequenceError,
    SequenceNotEditableError,
)
from core.session.shot import TimeLanes

from .sequence_widget_ui import Ui_SequenceWidget
from ..logger import logger
from ..parameter_tables_editor import ParametersEditor
from ..sequence_iteration_editors import create_default_editor
from ..timelanes_editor import (
    TimeLanesEditor,
    LaneDelegateFactory,
    LaneModelFactory,
)


def create_default_iteration_config() -> IterationConfiguration:
    return StepsConfiguration(steps=[])


@attrs.define
class _SequenceInfo:
    sequence_path: PureSequencePath
    sequence_parameters: Optional[ParameterNamespace]
    iteration_config: IterationConfiguration
    time_lanes: TimeLanes
    state: State


class SequenceWidget(QWidget, Ui_SequenceWidget):
    """Widget for editing sequence parameters, iterations and time lanes.

    This widget is a tab widget with three tabs: one for defining initial parameters, one for editing how the
    parameters should be iterated over for the sequence, and one for editing the time lanes that specify how
    a given shot should be executed.

    This widget is (optionally) associated with a sequence and displays the iteration
    configuration and time lanes for that sequence.
    If the widget is not associated with a sequence, it will hide itself.

    When associated with a sequence, the widget is constantly watching the state of the
    sequence.
    If the sequence is not in the draft state, the iteration editor and time lanes editor
    will become read-only.
    If the sequence is in the draft state, the iteration editor and time lanes editor
    will become editable and any change will be saved.
    """

    sequence_changed = Signal(object)  # Optional[tuple[PureSequencePath, State]]

    sequence_editable_set = Signal(_SequenceInfo)
    sequence_not_editable_set = Signal(_SequenceInfo)
    sequence_cleared = Signal()

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        lane_model_factory: LaneModelFactory,
        lane_delegate_factory: LaneDelegateFactory,
        parent: Optional[QWidget] = None,
    ):
        """Initializes the sequence widget.

        The sequence widget will initially be associated with no sequence.

        Args:
            session_maker: It is used to connect to the storage system in which to look
            for the sequence.
            lane_model_factory: A factory function that returns a lane model for a
            given lane.
            This is used to customize how a lane should be displayed and edited.
            When the timelanes editor needs to display a lane, the factory is called
            with the lane as argument.
            The factory should return a subclass of TimeLaneModel that is used as the
            model for the lane row.
            lane_delegate_factory: A factory function that returns a lane delegate for
            a given lane.
            It can optionally return a QStyledItemDelegate that is used to further
            customize how a lane should be displayed and edited.
            parent: The parent widget.
        """

        super().__init__(parent)
        self.setupUi(self)
        self.session_maker = session_maker
        self.lane_model_factory = lane_model_factory
        self.lane_delegate_factory = lane_delegate_factory

        with self.session_maker() as session:
            device_configurations = dict(session.default_device_configurations)

        self.time_lanes_editor = TimeLanesEditor(
            lane_model_factory,
            lane_delegate_factory,
            device_configurations,
            self,
        )

        self.parameters_editor = ParametersEditor(self)

        self.state_watcher_thread = self.StateWatcherThread(self)
        self.state_machine = QStateMachine(self)

        self.state_no_sequence = QState()
        self.state_sequence = SequenceSetState()
        self.state_sequence_editable = QState(self.state_sequence)
        self.state_sequence_not_editable = QState(self.state_sequence)

        self.state_no_sequence.addTransition(
            self.sequence_editable_set, self.state_sequence_editable
        )
        self.state_no_sequence.addTransition(
            self.sequence_not_editable_set, self.state_sequence_not_editable
        )
        self.state_sequence.addTransition(self.sequence_cleared, self.state_no_sequence)
        self.state_sequence.addTransition(
            self.sequence_not_editable_set, self.state_sequence_not_editable
        )
        self.state_sequence.addTransition(
            self.sequence_editable_set, self.state_sequence_editable
        )

        self.state_no_sequence.entered.connect(self.on_sequence_unset)
        self.state_sequence.entered.connect(self.on_sequence_set)
        self.state_sequence_editable.entered.connect(self.on_sequence_became_editable)
        self.state_sequence_not_editable.entered.connect(
            self.on_sequence_became_not_editable
        )

        self.state_machine.addState(self.state_no_sequence)
        self.state_machine.addState(self.state_sequence)
        self.state_machine.setInitialState(self.state_no_sequence)
        self.state_machine.start()

        self.setup_connections()

    def __enter__(self):
        """Starts the watcher thread to monitor the sequence state."""

        logger.debug("Entering SequenceWidget")
        self.state_watcher_thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Stops the state watcher thread."""

        logger.debug("Exiting SequenceWidget")
        self.state_watcher_thread.quit()
        self.state_watcher_thread.wait()
        return False

    def on_sequence_unset(self):
        self.setVisible(False)
        self.sequence_changed.emit(None)

    def on_sequence_set(self):
        previous_index = self.tabWidget.currentIndex()
        self.tabWidget.clear()
        self.iteration_editor = create_default_editor(
            self.state_sequence.iteration_config
        )
        self.iteration_editor.iteration_changed.connect(
            self.on_sequence_iteration_edited
        )
        self.tabWidget.addTab(self.parameters_editor, "&Globals")
        self.tabWidget.addTab(self.iteration_editor, "&Parameters")
        self.time_lanes_editor.blockSignals(True)
        self.time_lanes_editor.set_time_lanes(self.state_sequence.time_lanes)
        self.time_lanes_editor.blockSignals(False)
        self.tabWidget.addTab(self.time_lanes_editor, "&Time lanes")
        self.tabWidget.setCurrentIndex(previous_index)
        self.setVisible(True)
        self.sequence_changed.emit(
            (self.state_sequence.sequence_path, self.state_sequence.sequence_state)
        )

    def on_sequence_became_editable(self):
        self.iteration_editor.set_read_only(False)
        self.time_lanes_editor.set_read_only(False)
        self.parameters_editor.set_read_only(False)
        self.tabWidget.setTabVisible(0, False)

    def on_sequence_became_not_editable(self):
        self.iteration_editor.set_read_only(True)
        self.time_lanes_editor.set_read_only(True)
        self.parameters_editor.set_read_only(True)
        if self.state_sequence.sequence_parameters is not None:
            self.parameters_editor.set_parameters(
                self.state_sequence.sequence_parameters
            )
            self.tabWidget.setTabVisible(0, True)

    def set_sequence(self, sequence_path: Optional[PureSequencePath]) -> None:
        if sequence_path is None:
            self.sequence_cleared.emit()
        else:
            with self.session_maker() as session:
                stats = unwrap(session.sequences.get_stats(sequence_path))
                if stats.state in (State.DRAFT, State.PREPARING):
                    global_parameters = None
                else:
                    global_parameters = session.sequences.get_global_parameters(
                        sequence_path
                    )
                sequence_info = _SequenceInfo(
                    sequence_path=sequence_path,
                    sequence_parameters=global_parameters,
                    iteration_config=session.sequences.get_iteration_configuration(
                        sequence_path
                    ),
                    time_lanes=session.sequences.get_time_lanes(sequence_path),
                    state=unwrap(session.sequences.get_stats(sequence_path)).state,
                )
            if sequence_info.state.is_editable():
                self.sequence_editable_set.emit(sequence_info)
            else:
                self.sequence_not_editable_set.emit(sequence_info)

    def setup_connections(self):
        self.time_lanes_editor.time_lanes_changed.connect(self.on_time_lanes_edited)
        self.state_watcher_thread.change_detected.connect(self.set_sequence)

    def on_sequence_iteration_edited(self, iterations: IterationConfiguration):
        if self.state_sequence in self.state_machine.configuration():
            sequence = Sequence(self.state_sequence.sequence_path)
            with self.session_maker() as session:
                try:
                    session.sequences.set_iteration_configuration(sequence, iterations)
                except SequenceNotEditableError:
                    state = sequence.get_state(session)
                    iterations = session.sequences.get_iteration_configuration(
                        self.state_sequence.sequence_path
                    )
                    self.sequence_not_editable_set.emit(
                        _SequenceInfo(
                            sequence_path=self.state_sequence.sequence_path,
                            sequence_parameters=self.state_sequence.sequence_parameters,
                            iteration_config=iterations,
                            time_lanes=self.state_sequence.time_lanes,
                            state=state,
                        )
                    )
                else:
                    self.state_sequence.iteration_config = iterations

    def on_time_lanes_edited(self, time_lanes: TimeLanes):
        logger.debug("Time lanes edited")
        if self.state_sequence in self.state_machine.configuration():
            sequence = Sequence(self.state_sequence.sequence_path)
            with self.session_maker() as session:
                try:
                    session.sequences.set_time_lanes(
                        self.state_sequence.sequence_path, time_lanes
                    )
                except SequenceNotEditableError:
                    time_lanes = session.sequences.get_time_lanes(
                        self.state_sequence.sequence_path
                    )
                    self.sequence_not_editable_set.emit(
                        _SequenceInfo(
                            sequence_path=self.state_sequence.sequence_path,
                            sequence_parameters=self.state_sequence.sequence_parameters,
                            iteration_config=self.state_sequence.iteration_config,
                            time_lanes=time_lanes,
                            state=self.state_sequence.sequence_state,
                        )
                    )
                else:
                    self.state_sequence.time_lanes = time_lanes

    def closeEvent(self, event):
        self.state_watcher_thread.quit()
        self.state_watcher_thread.wait()
        super().closeEvent(event)

    class StateWatcherThread(QThread):
        change_detected = Signal(object)  # Optional[PureSequencePath]

        def __init__(self, sequence_widget: SequenceWidget):
            super().__init__(sequence_widget)
            self.sequence_widget = sequence_widget

        def run(self) -> None:
            def watch():
                if (
                    self.sequence_widget.state_sequence
                    in self.sequence_widget.state_machine.configuration()
                ):
                    sequence_path = self.sequence_widget.state_sequence.sequence_path
                    sequence = Sequence(sequence_path)
                    with self.sequence_widget.session_maker() as session:
                        try:
                            state = sequence.get_state(session)
                            iteration_config = sequence.get_iteration_configuration(
                                session
                            )
                            timelanes = sequence.get_time_lanes(session)
                        except (PathNotFoundError, PathIsNotSequenceError):
                            self.change_detected.emit(None)
                            return
                    if (
                        iteration_config
                        != self.sequence_widget.state_sequence.iteration_config
                    ):
                        self.change_detected.emit(sequence_path)
                    if timelanes != self.sequence_widget.state_sequence.time_lanes:
                        self.change_detected.emit(sequence_path)
                    if state != self.sequence_widget.state_sequence.sequence_state:
                        self.change_detected.emit(sequence_path)

            timer = QTimer()
            timer.timeout.connect(watch)
            timer.start(50)
            self.exec()
            timer.stop()


class SequenceSetState(QState):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sequence_info: Optional[_SequenceInfo] = None

    @property
    def sequence_state(self) -> State:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        return self._sequence_info.state

    @property
    def sequence_path(self) -> PureSequencePath:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        return self._sequence_info.sequence_path

    @property
    def sequence_parameters(self) -> Optional[ParameterNamespace]:
        return self._sequence_info.sequence_parameters

    @sequence_parameters.setter
    def sequence_parameters(self, value: ParameterNamespace) -> None:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        self._sequence_info.sequence_parameters = value

    @property
    def iteration_config(self) -> IterationConfiguration:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        return self._sequence_info.iteration_config

    @iteration_config.setter
    def iteration_config(self, value: IterationConfiguration) -> None:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        self._sequence_info.iteration_config = value

    @property
    def time_lanes(self) -> TimeLanes:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        return self._sequence_info.time_lanes

    @time_lanes.setter
    def time_lanes(self, value: TimeLanes) -> None:
        if self._sequence_info is None:
            raise ValueError("Sequence info not set")
        self._sequence_info.time_lanes = value

    def onEntry(self, event: QEvent) -> None:
        super().onEntry(event)
        if isinstance(event, QStateMachine.SignalEvent):
            assert len(event.arguments()) == 1
            info = event.arguments()[0]
            assert isinstance(info, _SequenceInfo)
            self._sequence_info = info

    def onExit(self, event: QEvent) -> None:
        super().onExit(event)
        self._sequence_info = None
