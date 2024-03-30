import copy
import functools

from PySide6 import QtCore
from PySide6.QtWidgets import (
    QMenu,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QApplication,
)

from caqtus.gui.common.qtutil import temporary_widget
from caqtus.gui.common.sequence_hierarchy import PathHierarchyView
from caqtus.gui.common.waiting_widget import run_with_wip_widget
from caqtus.session import ExperimentSessionMaker, PureSequencePath
from caqtus.session.path import InvalidPathFormatError
from caqtus.session.path_hierarchy import PathHasChildrenError
from caqtus.session.result import unwrap
from caqtus.session.sequence import State
from caqtus.session.sequence.iteration_configuration import (
    StepsConfiguration,
    ArangeLoop,
    ExecuteShot,
)
from caqtus.session.sequence_collection import PathIsSequenceError
from caqtus.session.shot import TimeLanes
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName
from .icons import get_icon

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


class EditablePathHierarchyView(PathHierarchyView):
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

    def show_context_menu(self, pos):
        index = self.indexAt(pos)

        path = self._model.get_path(self._proxy_model.mapToSource(index))

        with temporary_widget(QMenu(self)) as menu:
            color = self.palette().text().color()

            with self.session_maker() as session:
                is_sequence = unwrap(session.sequences.is_sequence(path))
                if is_sequence:
                    state = unwrap(session.sequences.get_state(path))
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
                    functools.partial(self.create_new_sequence, path)
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
                    functools.partial(self.on_sequence_duplication_requested, path)
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
                delete_action.triggered.connect(functools.partial(self.delete, path))

            menu.exec(self.mapToGlobal(pos))

    def on_clear_sequence_requested(self, path: PureSequencePath) -> None:
        """Clear the sequence at the given path.

        This will revert the sequence to the draft state, effectively clearing all
        the data in it.
        During the process, a waiting widget will be shown to the user to prevent them
        from interacting with the sequence while it is being cleared.
        """

        def clear():
            with self.session_maker() as session:
                session.sequences.set_state(path, State.DRAFT)

        run_with_wip_widget(self, "Clearing sequence", clear)

    def on_sequence_duplication_requested(self, path: PureSequencePath):
        """Ask the user for a new sequence name and duplicate the sequence."""

        assert not path.is_root()

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
            try:
                if text.startswith(PureSequencePath.separator()):
                    new_path = PureSequencePath(text)
                else:
                    assert path.parent is not None
                    new_path = path.parent / text
            except InvalidPathFormatError:
                QMessageBox.critical(
                    self,
                    title,
                    f"The path '{text}' is not a valid path.",
                )
                return
            with self.session_maker() as session:
                iterations = session.sequences.get_iteration_configuration(path)
                time_lanes = session.sequences.get_time_lanes(path)
                try:
                    session.sequences.create(
                        new_path,
                        iterations,
                        time_lanes,
                    )
                except PathIsSequenceError:
                    QMessageBox.critical(
                        self,
                        title,
                        f"Can't duplicate sequence '{path}' to '{new_path}' because "
                        f"'{new_path}' already exists and is a sequence.",
                    )
                except PathHasChildrenError:
                    QMessageBox.critical(
                        self,
                        title,
                        f"Can't duplicate sequence '{path}' to '{new_path}' because "
                        f"'{new_path}' already exists and has children.",
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

    def create_new_sequence(self, path: PureSequencePath):
        text, ok = QInputDialog().getText(
            self,
            f"New sequence in {path}...",
            "Sequence name:",
            QLineEdit.EchoMode.Normal,
            "new sequence",
        )
        if ok and text:
            new_path = path / text
            with self.session_maker() as session:
                session.sequences.create(
                    new_path,
                    copy.deepcopy(DEFAULT_ITERATION_CONFIG),
                    copy.deepcopy(DEFAULT_TIME_LANES),
                )

    def delete(self, path: PureSequencePath):
        message = (
            f'You are about to delete the path "{path}".\n'
            "All data inside will be irremediably lost."
        )
        if self.exec_confirmation_message_box(message):
            with self.session_maker() as session:
                if unwrap(session.sequences.is_sequence(path)):
                    session.paths.delete_path(path, delete_sequences=True)
                else:
                    # An error will be raised if someone tries to delete a folder that
                    # contains sequences.
                    try:
                        session.paths.delete_path(path, delete_sequences=False)
                    except PathIsSequenceError:
                        QMessageBox.critical(
                            self,
                            QApplication.instance().applicationName(),
                            f"The path '{path}' contains sequences and therefore "
                            f"cannot be deleted",
                        )

    def exec_confirmation_message_box(self, message: str) -> bool:
        """Show a popup box to ask  a question."""

        message_box = QMessageBox(self)
        app = QApplication.instance()
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
