from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QWidget

from core.session import ExperimentSessionMaker, PureSequencePath, BoundSequencePath
from core.session._return_or_raise import unwrap
from core.session.path_hierarchy import PathNotFoundError
from core.session.sequence import State, Sequence
from core.session.sequence_collection import (
    PathIsNotSequenceError,
    SequenceStats,
    SequenceNotEditableError,
)
from core.session.shot import TimeLanes
from waiting_widget import run_with_wip_widget
from .sequence_widget_ui import Ui_SequenceWidget
from ..sequence_iteration_editors import create_default_editor
from ..timelanes_editor import TimeLanesEditor


class SequenceWidget(QWidget, Ui_SequenceWidget):
    sequence_start_requested = pyqtSignal(PureSequencePath)
    sequence_interruption_requested = pyqtSignal(PureSequencePath)

    def __init__(
        self,
        sequence: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.session_maker = session_maker
        self.sequence_path = sequence

        with self.session_maker() as session:
            sequence = Sequence(self.sequence_path)
            iteration_config = sequence.get_iteration_configuration(session)
            time_lanes = sequence.get_time_lanes(session)
            stats = unwrap(session.sequences.get_stats(self.sequence_path))
        self.iteration_editor = create_default_editor(iteration_config)
        self.iteration_editor.iteration_changed.connect(
            self.on_sequence_iteration_changed
        )
        self.apply_state(stats.state)
        self.tabWidget.clear()
        self.tabWidget.addTab(self.iteration_editor, "Iteration")
        self.time_lanes_editor = TimeLanesEditor(self)
        self.time_lanes_editor.set_time_lanes(time_lanes)
        self.time_lanes = time_lanes
        self.time_lanes_editor.time_lanes_changed.connect(self.on_time_lanes_changed)
        self.tabWidget.addTab(self.time_lanes_editor, "Shot")

        self.state_watcher_thread = self.StateWatcherThread(self)

        self.setup_connections()
        self.state_watcher_thread.start()

    def setup_connections(self):
        self.start_button.clicked.connect(
            lambda _: self.sequence_start_requested.emit(self.sequence_path)
        )
        self.clear_button.clicked.connect(self.clear_sequence)
        self.interrupt_button.clicked.connect(
            lambda _: self.sequence_interruption_requested.emit(self.sequence_path)
        )
        self.state_watcher_thread.sequence_not_found.connect(self.deleteLater)
        self.state_watcher_thread.stats_changed.connect(self.apply_stats)
        self.state_watcher_thread.time_lanes_changed.connect(
            self.time_lanes_editor.set_time_lanes
        )

    def clear_sequence(self):
        def clear():
            with self.session_maker() as session:
                session.sequences.set_state(self.sequence_path, State.DRAFT)

        run_with_wip_widget(self, "Clearing sequence", clear)

    def on_sequence_iteration_changed(self):
        iterations = self.iteration_editor.get_iteration()
        with self.session_maker() as session:
            try:
                session.sequences.set_iteration_configuration(
                    Sequence(BoundSequencePath(self.sequence_path, session)), iterations
                )
            except SequenceNotEditableError:
                iterations = session.sequences.get_iteration_configuration(
                    self.sequence_path
                )
                self.iteration_editor.set_iteration(iterations)

    def on_time_lanes_changed(self):
        time_lanes = self.time_lanes_editor.get_time_lanes()
        with self.session_maker() as session:
            try:
                session.sequences.set_time_lanes(
                    self.sequence_path, time_lanes
                )
            except SequenceNotEditableError:
                time_lanes = session.sequences.get_time_lanes(
                    self.sequence_path
                )
                self.time_lanes_editor.set_time_lanes(time_lanes)
            finally:
                self.time_lanes = time_lanes

    def apply_stats(self, stats: SequenceStats):
        self.apply_state(stats.state)

    def closeEvent(self, event):
        self.state_watcher_thread.quit()
        self.state_watcher_thread.wait()
        super().closeEvent(event)

    def apply_state(self, state: State):
        self.iteration_editor.set_read_only(not state.is_editable())
        if state == State.DRAFT:
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)
        if state in {State.RUNNING}:
            self.interrupt_button.setEnabled(True)
        else:
            self.interrupt_button.setEnabled(False)
        if state in {State.FINISHED, State.INTERRUPTED, State.CRASHED}:
            self.clear_button.setEnabled(True)
        else:
            self.clear_button.setEnabled(False)

    class StateWatcherThread(QThread):
        stats_changed = pyqtSignal(SequenceStats)
        sequence_not_found = pyqtSignal()
        time_lanes_changed = pyqtSignal(TimeLanes)

        def __init__(self, sequence_widget: SequenceWidget):
            super().__init__(sequence_widget)
            self.sequence_widget = sequence_widget
            with self.sequence_widget.session_maker() as session:
                self.stats = unwrap(
                    session.sequences.get_stats(
                        self.sequence_widget.sequence_path
                    )
                )

        def run(self) -> None:
            def watch():
                with self.sequence_widget.session_maker() as session:
                    try:
                        stats = unwrap(
                            session.sequences.get_stats(
                                self.sequence_widget.sequence_path
                            )
                        )
                        if stats != self.stats:
                            self.stats = stats
                            self.stats_changed.emit(stats)
                        time_lanes = session.sequences.get_time_lanes(
                            self.sequence_widget.sequence_path
                        )
                        if time_lanes != self.sequence_widget.time_lanes:
                            self.time_lanes_changed.emit(time_lanes)
                    except (PathNotFoundError, PathIsNotSequenceError):
                        self.sequence_not_found.emit()
                        self.quit()

            timer = QTimer()
            timer.timeout.connect(watch)
            timer.start(50)
            self.exec()
            timer.stop()
