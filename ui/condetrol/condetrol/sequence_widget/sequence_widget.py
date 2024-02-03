from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QWidget
from condetrol.sequence_iteration_editors import SequenceIterationEditor
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
    sequence_start_requested = pyqtSignal(PureSequencePath)
    sequence_interruption_requested = pyqtSignal(PureSequencePath)

    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        lane_model_factory: LaneModelFactory,
        lane_delegate_factory: LaneDelegateFactory,
        parent: Optional[QWidget] = None,
    ):
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

        self.sequence_path: Optional[PureSequencePath]
        self.iteration_editor: SequenceIterationEditor
        self.time_lanes: TimeLanes
        self.iterations: IterationConfiguration
        self.set_sequence(None)

        self.setup_connections()

    def set_sequence(self, sequence_path: Optional[PureSequencePath]) -> None:
        self.state_watcher_thread.quit()
        self.state_watcher_thread.wait()
        self.sequence_path = sequence_path
        previous_index = self.tabWidget.currentIndex()
        self.tabWidget.clear()

        if sequence_path is None:
            iteration_config = create_default_iteration_config()
        else:
            with self.session_maker() as session:
                iteration_config = session.sequences.get_iteration_configuration(
                    sequence_path
                )
        self.iteration_editor = create_default_editor(iteration_config)
        self.iteration_editor.iteration_changed.connect(
            self.on_sequence_iteration_changed
        )
        self.tabWidget.addTab(self.iteration_editor, "Iterations")

        if sequence_path is not None:
            with self.session_maker() as session:
                time_lanes = session.sequences.get_time_lanes(sequence_path)
            self.time_lanes_editor.blockSignals(True)
            self.time_lanes_editor.set_time_lanes(time_lanes)
            self.time_lanes_editor.blockSignals(False)
        else:
            time_lanes = self.time_lanes_editor.get_time_lanes()
        self.tabWidget.addTab(self.time_lanes_editor, "Timelanes")
        if sequence_path is None:
            self.setVisible(False)
        else:
            self.setVisible(True)
        self.tabWidget.setCurrentIndex(previous_index)
        self.time_lanes = time_lanes
        self.iterations = iteration_config
        self.state_watcher_thread.start()

    def setup_connections(self):
        self.time_lanes_editor.time_lanes_changed.connect(self.on_time_lanes_changed)
        self.state_watcher_thread.state_changed.connect(self.apply_state)
        self.state_watcher_thread.time_lanes_changed.connect(
            self.time_lanes_editor.set_time_lanes
        )

    def on_sequence_iteration_changed(self):
        iterations = self.iteration_editor.get_iteration()
        with self.session_maker() as session:
            try:
                session.sequences.set_iteration_configuration(
                    Sequence(self.sequence_path), iterations
                )
            except SequenceNotEditableError:
                iterations = session.sequences.get_iteration_configuration(
                    self.sequence_path
                )
                self.iteration_editor.set_iteration(iterations)
            finally:
                self.iterations = iterations

    def on_time_lanes_changed(self):
        time_lanes = self.time_lanes_editor.get_time_lanes()
        with self.session_maker() as session:
            try:
                session.sequences.set_time_lanes(self.sequence_path, time_lanes)
            except SequenceNotEditableError:
                time_lanes = session.sequences.get_time_lanes(self.sequence_path)
                self.time_lanes_editor.set_time_lanes(time_lanes)
            finally:
                self.time_lanes = time_lanes

    def closeEvent(self, event):
        self.state_watcher_thread.quit()
        self.state_watcher_thread.wait()
        super().closeEvent(event)

    def apply_state(self, state: State):
        self.iteration_editor.set_read_only(not state.is_editable())
        self.time_lanes_editor.set_read_only(not state.is_editable())

    class StateWatcherThread(QThread):
        state_changed = pyqtSignal(object)  # Optional[State]
        time_lanes_changed = pyqtSignal(TimeLanes)
        iteration_changed = pyqtSignal(IterationConfiguration)

        def __init__(self, sequence_widget: SequenceWidget):
            super().__init__(sequence_widget)
            self.sequence_widget = sequence_widget
            self.state: Optional[State] = None

        def get_state(self) -> Optional[State]:
            try:
                with self.sequence_widget.session_maker() as session:
                    stats = unwrap(
                        session.sequences.get_stats(self.sequence_widget.sequence_path)
                    )
                return stats.state
            except (PathNotFoundError, PathIsNotSequenceError):
                return None

        def run(self) -> None:
            def watch():
                state = self.get_state()
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
