from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, QTimer, Signal, QEvent
from PySide6.QtStateMachine import QStateMachine, QState
from PySide6.QtWidgets import QWidget
from core.session import ExperimentSessionMaker, PureSequencePath
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
from ..sequence_iteration_editors import create_default_editor
from ..timelanes_editor import (
    TimeLanesEditor,
    LaneDelegateFactory,
    LaneModelFactory,
)


def create_default_iteration_config() -> IterationConfiguration:
    return StepsConfiguration(steps=[])


class SequenceWidget(QWidget, Ui_SequenceWidget):
    """Widget for editing sequence iterations and timelanes.

    This widget is a tab widget with two tabs: one for editing how the parameters should
    be iterated over for a sequence, and one for editing the timelanes that specify how
    a given shot should be executed.

    This widget is (optionally) associated with a sequence and displays the iteration
    configuration and timelanes for that sequence.
    If the widget is not associated with a sequence, it will hide itself.

    When associated with a sequence, the widget is constantly watching the state of the
    sequence.
    If the sequence is not in the draft state, the iteration editor and timelanes editor
    will become read-only.
    If the sequence is in the draft state, the iteration editor and timelanes editor
    will become editable and any change will be saved.
    """

    sequence_editable_set = Signal(PureSequencePath, IterationConfiguration, TimeLanes)
    sequence_not_editable_set = Signal(
        PureSequencePath, IterationConfiguration, TimeLanes
    )
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
            device_configurations = dict(session.device_configurations)
            constant_tables = dict(session.constants)

        self.time_lanes_editor = TimeLanesEditor(
            lane_model_factory,
            lane_delegate_factory,
            device_configurations,
            constant_tables,
            self,
        )

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

    def on_sequence_unset(self):
        print("Sequence unset")
        self.setVisible(False)

    def on_sequence_set(self):
        print("Sequence set")
        previous_index = self.tabWidget.currentIndex()
        self.tabWidget.clear()
        self.iteration_editor = create_default_editor(
            self.state_sequence.iteration_config
        )
        self.iteration_editor.iteration_changed.connect(
            self.on_sequence_iteration_edited
        )
        self.tabWidget.addTab(self.iteration_editor, "Iterations")
        self.time_lanes_editor.blockSignals(True)
        self.time_lanes_editor.set_time_lanes(self.state_sequence.timelanes)
        self.time_lanes_editor.blockSignals(False)
        self.tabWidget.addTab(self.time_lanes_editor, "Timelanes")
        self.tabWidget.setCurrentIndex(previous_index)
        self.setVisible(True)

    def on_sequence_became_editable(self):
        self.iteration_editor.set_read_only(False)
        self.time_lanes_editor.set_read_only(False)

    def on_sequence_became_not_editable(self):
        self.iteration_editor.set_read_only(True)
        self.time_lanes_editor.set_read_only(True)

    def set_sequence(self, sequence_path: Optional[PureSequencePath]) -> None:
        if sequence_path is None:
            self.sequence_cleared.emit()
        else:
            with self.session_maker() as session:
                state = unwrap(session.sequences.get_stats(sequence_path)).state
                iteration_config = session.sequences.get_iteration_configuration(
                    sequence_path
                )
                timelanes = session.sequences.get_time_lanes(sequence_path)
            if state.is_editable():
                self.sequence_editable_set.emit(
                    sequence_path, iteration_config, timelanes
                )
            else:
                self.sequence_not_editable_set.emit(
                    sequence_path, iteration_config, timelanes
                )

    def setup_connections(self):
        self.time_lanes_editor.time_lanes_changed.connect(self.on_time_lanes_edited)
        self.state_watcher_thread.state_changed.connect(self.apply_state)
        self.state_watcher_thread.time_lanes_changed.connect(
            self.time_lanes_editor.set_time_lanes
        )

    def on_sequence_iteration_edited(self, iterations: IterationConfiguration):
        if self.state_sequence in self.state_machine.configuration():
            sequence = Sequence(self.state_sequence.sequence_path)
            with self.session_maker() as session:
                try:
                    session.sequences.set_iteration_configuration(sequence, iterations)
                except SequenceNotEditableError:
                    iterations = session.sequences.get_iteration_configuration(
                        self.state_sequence.sequence_path
                    )
                    self.sequence_not_editable_set.emit(
                        self.state_sequence.sequence_path,
                        iterations,
                        self.state_sequence.timelanes,
                    )
                else:
                    self.state_sequence.iteration_config = iterations

    def on_time_lanes_edited(self, timelanes: TimeLanes):
        if self.state_sequence in self.state_machine.configuration():
            with self.session_maker() as session:
                try:
                    session.sequences.set_time_lanes(
                        self.state_sequence.sequence_path,
                        timelanes
                    )
                except SequenceNotEditableError:
                    timelanes = session.sequences.get_time_lanes(
                        self.state_sequence.sequence_path
                    )
                    self.sequence_not_editable_set.emit(
                        self.state_sequence.sequence_path,
                        self.state_sequence.iteration_config,
                        timelanes,
                    )
                else:
                    self.state_sequence.timelanes = timelanes

    def closeEvent(self, event):
        self.state_watcher_thread.quit()
        self.state_watcher_thread.wait()
        super().closeEvent(event)

    def apply_state(self, state: Optional[State]):
        if state is None:
            self.set_sequence(None)
        else:
            self.iteration_editor.set_read_only(not state.is_editable())
            self.time_lanes_editor.set_read_only(not state.is_editable())

    class StateWatcherThread(QThread):
        state_changed = Signal(object)  # Optional[State]
        time_lanes_changed = Signal(TimeLanes)
        iteration_changed = Signal(IterationConfiguration)

        def __init__(self, sequence_widget: SequenceWidget):
            super().__init__(sequence_widget)
            self.sequence_widget = sequence_widget
            self._sequence_and_state: Optional[tuple[PureSequencePath, State]] = None

        @property
        def sequence_path(self) -> Optional[PureSequencePath]:
            return self._sequence_and_state[0] if self._sequence_and_state else None

        @property
        def state(self) -> Optional[State]:
            return self._sequence_and_state[1] if self._sequence_and_state else None

        def get_state(self) -> Optional[State]:
            if self.sequence_path is None:
                return None
            try:
                with self.sequence_widget.session_maker() as session:
                    stats = unwrap(session.sequences.get_stats(self.sequence_path))
                return stats.state
            except (PathNotFoundError, PathIsNotSequenceError):
                return None

        def run(self) -> None:
            def watch():
                state = self.sequence_widget.get_state()
                if state != self.state:
                    self.state = state
                    self.state_changed.emit(state)
                with self.sequence_widget.session_maker() as session:
                    try:
                        time_lanes = session.sequences.get_time_lanes(
                            self.sequence_widget.sequence_path
                        )
                        iterations = session.sequences.get_iteration_configuration(
                            self.sequence_widget.sequence_path
                        )
                    except (PathNotFoundError, PathIsNotSequenceError):
                        pass
                    else:
                        if time_lanes != self.sequence_widget.time_lanes:
                            self.time_lanes_changed.emit(time_lanes)
                        if iterations != self.sequence_widget.iterations:
                            self.iteration_changed.emit(iterations)

            timer = QTimer()
            timer.timeout.connect(watch)
            timer.start(50)
            self.exec()
            timer.stop()


class SequenceSetState(QState):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sequence_path: Optional[PureSequencePath] = None
        self._iteration_config: Optional[IterationConfiguration] = None
        self._timelanes: Optional[TimeLanes] = None

    @property
    def sequence_path(self) -> PureSequencePath:
        if self._sequence_path is None:
            raise ValueError("Sequence path not set")

        return self._sequence_path

    @property
    def iteration_config(self) -> IterationConfiguration:
        if self._iteration_config is None:
            raise ValueError("Iteration config not set")
        return self._iteration_config

    @iteration_config.setter
    def iteration_config(self, value: IterationConfiguration) -> None:
        self._iteration_config = value

    @property
    def timelanes(self) -> TimeLanes:
        if self._timelanes is None:
            raise ValueError("Timelanes not set")
        return self._timelanes

    @timelanes.setter
    def timelanes(self, value: TimeLanes) -> None:
        self._timelanes = value

    def onEntry(self, event: QEvent) -> None:
        super().onEntry(event)
        if isinstance(event, QStateMachine.SignalEvent):
            self._sequence_path = event.arguments()[0]
            self._iteration_config = event.arguments()[1]
            self._timelanes = event.arguments()[2]

    def onExit(self, event: QEvent) -> None:
        super().onExit(event)
        self._sequence_path = None
