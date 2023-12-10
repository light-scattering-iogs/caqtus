import logging
import time
from functools import partial
from logging.handlers import QueueListener
from multiprocessing.managers import BaseManager
from typing import Callable, Optional, ParamSpec, TypeVar

from PyQt6 import QtCore
from PyQt6.QtCore import QSettings, QModelIndex, Qt, QTimer, QThread
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QPalette,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenu,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QTextBrowser,
    QWidget,
    QApplication,
    QFileDialog,
)

from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker
from experiment_control.manager import ExperimentManager
from sequence.runtime import Sequence, State
from sequence_hierarchy import EditableSequenceHierarchyModel, SequenceHierarchyDelegate
from util import serialization
from waiting_widget.spinner import WaitingSpinner
from .config_editor import ConfigEditor
from .current_experiment_config_watcher import CurrentExperimentConfigWatcher
from .experiment_viewer_ui import Ui_MainWindow
from .sequence_widget import SequenceWidget

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


ExperimentProcessManager.register("connect_to_experiment_manager")
ExperimentProcessManager.register("get_logs_queue")


class TextBrowser(QTextBrowser):
    def sizeHint(self) -> QtCore.QSize:
        size = super().sizeHint()
        return QtCore.QSize(size.width(), 0)


class CustomFormatter(logging.Formatter):
    header = (
        "<b>%(levelname)s</b> %(asctime)s - <a"
        " href=%(pathname)s:%(lineno)d>%(pathname)s:%(lineno)d</a>"
    )

    FORMATS = {
        logging.DEBUG: (
            "<span style='color:grey;white-space:"
            f" pre-wrap'>{header} %(message)s</span>"
        ),
        logging.INFO: (
            "<span"
            f" style='color:white;white-space:pre-wrap'>{header} %(message)s</span>"
        ),
        logging.WARNING: (
            "<span"
            f" style='color:yellow;white-space:pre-wrap'>{header} %(message)s</span>"
        ),
        logging.ERROR: (
            f"<span style='color:red;white-space: pre-wrap'>{header} %(message)s</span>"
        ),
        logging.CRITICAL: f"<span style='color:red';>{header} %(message)s</span>",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class TextBrowserEditLogger(logging.Handler, QtCore.QObject):
    append_text = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        QtCore.QObject.__init__(self)
        self.widget = TextBrowser(parent)
        self.widget.setOpenExternalLinks(True)
        self.widget.setReadOnly(True)
        self.append_text.connect(self.widget.append)

    def emit(self, record):
        msg = self.format(record)
        self.append_text.emit(msg)


class ExperimentViewer(QMainWindow, Ui_MainWindow):
    """Main window of the application

    It contains a file explorer to navigate the sequences and when clicking on a
    sequence, opens it in a dockable widget.
    """

    def __init__(self, session_maker: ExperimentSessionMaker, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")
        self._experiment_session_maker = session_maker

        self._experiment_config_watcher = CurrentExperimentConfigWatcher(session_maker)

        self.setupUi(self)

        # restore window geometry from last session
        self.restoreState(self.ui_settings.value(f"{__name__}/state", self.saveState()))
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.action_edit_current_experiment_config.triggered.connect(
            self.edit_current_experiment_config
        )
        self.action_save_current_experiment_config.triggered.connect(
            self.save_current_experiment_config
        )
        self.action_load_current_experiment_config.triggered.connect(
            self.load_current_experiment_config
        )

        self.model = EditableSequenceHierarchyModel(
            session_maker=self._experiment_session_maker, parent=self.sequences_view
        )
        self.sequences_view.setModel(self.model)

        # special delegate that show progress bar
        delegate = SequenceHierarchyDelegate(self.sequences_view)
        self.sequences_view.setItemDelegateForColumn(1, delegate)

        # context menu that let manage a sequence/folder
        self.sequences_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sequences_view.customContextMenuRequested.connect(self.show_context_menu)
        self.sequences_view.doubleClicked.connect(self.sequence_view_double_clicked)
        self.sequences_view.expanded.connect(
            lambda _: self.sequences_view.resizeColumnToContents(0)
        )

        # refresh the view to update the info in real time
        self.view_update_timer = QTimer(self)
        self.view_update_timer.timeout.connect(self.sequences_view.update)
        self.view_update_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.view_update_timer.start(500)

        self.dock_widget = QMainWindow()
        self.setCentralWidget(self.dock_widget)

        self.logs_handler = TextBrowserEditLogger()
        self.logs_dock.setWidget(self.logs_handler.widget)
        self.logs_handler.setFormatter(CustomFormatter())
        logging.getLogger().addHandler(self.logs_handler)
        logging.getLogger().setLevel(logging.DEBUG)

        self.experiment_process_manager = ExperimentProcessManager(
            address=("localhost", 60000), authkey=b"Deardear"
        )
        self.experiment_process_manager.connect()
        self.logs_listener = QueueListener(
            self.experiment_process_manager.get_logs_queue(), self.logs_handler  # type: ignore
        )
        self.logs_listener.start()
        self.worker = BlockingThread(self)

    def connect_to_experiment_manager(self) -> ExperimentManager:
        return self.experiment_process_manager.connect_to_experiment_manager()

    def __enter__(self):
        self._experiment_config_watcher.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._experiment_config_watcher.__exit__(exc_type, exc_value, traceback)

    def show_info_message(self, message: str, timeout: int = 5000) -> None:
        """Display a message in the info bar at the bottom of the window.

        Args:
            message: the message to display.
            timeout: the time in milliseconds after which the message will disappear.
        """

        logger.info(message)
        self.status_bar.showMessage(message, timeout)

    def show_error_message(
        self, message: str, exception: Optional[Exception] = None
    ) -> None:
        """Display an error message in the info bar at the bottom of the window."""

        if exception is not None:
            logger.error(message, exc_info=exception)
        else:
            logger.error(message)
        self.status_bar.showMessage(message, 5000)

    def sequence_view_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        if path := self.model.get_path(index):
            sequence_widget = SequenceWidget(
                Sequence(path),
                self._experiment_config_watcher.get_current_config(),
                self._experiment_session_maker,
            )
            self.dock_widget.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, sequence_widget
            )

    def show_context_menu(self, position):
        index = self.sequences_view.indexAt(position)

        menu = QMenu(self.sequences_view)

        is_deletable = True
        can_create = False

        if index.isValid():
            if self.model.is_sequence(index):
                stats = self.model.get_sequence_stats(index)
                state = stats.state
                if state == State.DRAFT:
                    start_sequence_action = QAction("Start")
                    menu.addAction(start_sequence_action)
                    # noinspection PyUnresolvedReferences
                    start_sequence_action.triggered.connect(
                        lambda _: self.start_sequence(index),
                    )
                elif state == State.RUNNING:
                    is_deletable = False
                    interrupt_sequence_action = QAction("Interrupt")
                    menu.addAction(interrupt_sequence_action)
                    interrupt_sequence_action.triggered.connect(
                        self.interrupt_currently_running_sequence
                    )
                elif (
                    state == State.FINISHED
                    or state == State.INTERRUPTED
                    or state == State.CRASHED
                ):
                    clear_sequence_action = QAction("Remove data")
                    menu.addAction(clear_sequence_action)
                    clear_sequence_action.triggered.connect(
                        partial(self.revert_to_draft, index)
                    )

                duplicate_sequence_action = QAction("Duplicate")
                menu.addAction(duplicate_sequence_action)
                duplicate_sequence_action.triggered.connect(
                    partial(self.duplicate_sequence, index)
                )
            else:  # index is folder
                can_create = True
        else:
            can_create = True  # can create in the root level
        if can_create:
            new_menu = QMenu("New...")
            menu.addMenu(new_menu)

            create_folder_action = QAction("folder")
            new_menu.addAction(create_folder_action)
            create_folder_action.triggered.connect(
                partial(self.create_new_folder, index)
            )

            create_sequence_action = QAction("sequence")
            new_menu.addAction(create_sequence_action)
            create_sequence_action.triggered.connect(
                partial(self.create_new_sequence, index)
            )

        if index.isValid() and is_deletable:
            delete_action = QAction("Delete")
            menu.addAction(delete_action)
            delete_action.triggered.connect(partial(self.delete, index))

        menu.exec(self.sequences_view.mapToGlobal(position))

    def interrupt_currently_running_sequence(self) -> None:
        """Interrupt the currently running sequence.

        This method is not blocking. After calling this method, actual interruption of the sequence might take some time
        as it finishes the current shots, saves the data and performs cleanup. After calling this method, you should
        wait until `is_running` returns False.
        """

        if self.connect_to_experiment_manager().interrupt_sequence():
            self.show_info_message("Interruption requested.")
        else:
            self.show_info_message("No sequence is currently running.")

    def duplicate_sequence(self, index: QModelIndex) -> bool:
        """Duplicate a sequence

        Pop up a dialog to ask for a new name and duplicate the sequence at the given index to the new name in the same
        containing folder.
        Args:
            index: QModelIndex of the sequence to duplicate

        Returns:
            True if the sequence was successfully duplicated, False otherwise
        """
        path = self.model.get_path(index)
        if path is None:
            return False

        with self._experiment_session_maker() as session:
            if not path.is_sequence(session):
                return False

        text, ok = QInputDialog().getText(
            self,
            f"Duplicate sequence {path}...",
            "Destination:",
            QLineEdit.EchoMode.Normal,
            path.name,
        )
        if ok and text:
            duplicated = self.model.duplicate_sequence(index, text)
            self.sequences_view.update()
            return duplicated
        return False

    def start_sequence(self, index: QModelIndex):
        sequence_path = self.model.get_path(index)
        if sequence_path:
            with self._experiment_session_maker() as session:
                current_experiment_config = session.experiment_configs.get_current()
                if current_experiment_config is None:
                    self.show_error_message(
                        "No experiment config is currently set. Please set one before starting a sequence."
                    )
                else:
                    started = self.connect_to_experiment_manager().start_sequence(
                        current_experiment_config,
                        sequence_path,
                    )
                    if not started:
                        self.show_error_message(
                            "A sequence is already running. Please interrupt it before starting a new one."
                        )

    def create_new_folder(self, index: QModelIndex):
        if index.isValid():
            path = str(self.model.get_path(index))
        else:
            path = "root"
        text, ok = QInputDialog().getText(
            self,
            f"New folder in {path}...",
            "Folder name:",
            QLineEdit.EchoMode.Normal,
            "new_folder",
        )
        if ok and text:
            self.model.create_new_folder(index, text)
            self.sequences_view.update()

    def create_new_sequence(self, index: QModelIndex):
        if index.isValid():
            path = str(self.model.get_path(index))
        else:
            path = "root"
        text, ok = QInputDialog().getText(
            self,
            f"New sequence in {path}...",
            "Sequence name:",
            QLineEdit.EchoMode.Normal,
            "new_sequence",
        )
        if ok and text:
            self.model.create_new_sequence(index, text)
            self.sequences_view.update()

    def delete(self, index: QModelIndex):
        if index.isValid():
            path = str(self.model.get_path(index))
            message = (
                f'You are about to delete the path "{path}".\n'
                "All data inside will be irremediably lost."
            )
            if self.exec_confirmation_message_box(message):
                self.model.delete(index)
                self.sequences_view.update()

    def edit_current_experiment_config(self):
        """Edit the current experiment config.

        Open an editor displaying the current experiment config to allow the user to edit it.
        The editor is a modal dialog, so the user cannot interact with the rest of the application while the editor is
        open.
        If the config is modified when the editor is closed, the current config is updated in the database.
        """

        current_config = self._experiment_config_watcher.get_current_config()

        editor = ConfigEditor(current_config)
        editor.exec()
        new_experiment_config = editor.get_config()
        if current_config != new_experiment_config:
            self.change_current_experiment_config(new_experiment_config)
        else:
            self.show_info_message("The current experiment config was not modified.")

    def save_current_experiment_config(self) -> None:
        """Save the current experiment config to a file.

        Open a modal dialog to ask the user where to save the current experiment config.
        The config is saved as a JSON file.
        """

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save current experiment config",
            "",
            "JSON (*.json)",
        )
        if file_name:
            current_experiment_config = (
                self._experiment_config_watcher.get_current_config()
            )
            json_string = serialization.to_json(current_experiment_config)
            with open(file_name, "w") as f:
                f.write(json_string)
            self.show_info_message(
                f"Current experiment config was saved to {file_name}"
            )

    def load_current_experiment_config(self) -> None:
        """Load an experiment config from a file.

        Open a modal dialog to ask the user which file to load the experiment config from.
        The content of the file must be a JSON string with a valid representation of an experiment config.
        If the content of the file is not a valid experiment config, an error message is displayed, but no exception
        is raised.
        """

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load experiment config",
            "",
            "JSON (*.json)",
        )

        if not file_name:
            return

        try:
            with open(file_name, "r") as f:
                json_string = f.read()
        except Exception as e:
            self.show_error_message(f"Could not read the file {file_name}", e)
            return

        try:
            new_experiment_config = serialization.from_json(
                json_string, ExperimentConfig
            )
        except Exception as e:
            self.show_error_message(
                f"Could not construct the experiment config from {file_name}", e
            )
        else:
            self.change_current_experiment_config(new_experiment_config)

    def change_current_experiment_config(self, new_config: ExperimentConfig) -> None:
        """Write a new experiment config to the database."""

        with self._experiment_session_maker() as session:
            old_name = session.experiment_configs.get_current()
            # Here we set the current config to the new one in the database.
            # The experiment config watcher will detect the change and update the current config in the experiment
            # manager, so we don't have to do it explicitly here.
            new_name = session.experiment_configs.set_current_config(new_config)
        self.show_info_message(
            f"Current experiment config was updated from {old_name} to {new_name}"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        experiment_manager = self.connect_to_experiment_manager()
        if experiment_manager.is_running():
            message_box = create_on_close_message_box(self)
            result = message_box.exec()
            if result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif result == QMessageBox.StandardButton.Yes:
                experiment_manager.interrupt_sequence()
                while experiment_manager.is_running():
                    time.sleep(0.1)
            elif result == QMessageBox.StandardButton.No:
                pass

        self.save_window_state()
        self.view_update_timer.stop()

        # The following line waits to have all logs before closing, but for some reason, it blocks forever.
        # It is commented for now, but can cause some logs to be lost.
        # self.logs_listener.stop()

        self.model.on_destroy()
        super().closeEvent(event)

    def save_window_state(self):
        state = self.saveState()
        self.ui_settings.setValue(f"{__name__}/state", state)
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)

    def revert_to_draft(self, index: QModelIndex):
        """Remove all data files from a sequence"""

        if index.isValid():
            path = str(self.model.get_path(index))
            message = (
                f'You are about to revert the sequence "{path}" to draft.\n'
                "All associated data will be irremediably lost."
            )
            if self.exec_confirmation_message_box(message):

                def target():
                    self.model.revert_to_draft(index)

                self.worker.task = target
                self.worker.start()

                self.sequences_view.update()

    def exec_confirmation_message_box(self, message: str) -> bool:
        """Show a popup box to ask  a question"""

        message_box = QMessageBox(self)
        message_box.setWindowTitle("Caqtus")
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


_P = ParamSpec("_P")
_T = TypeVar("_T")


class BlockingThread(QThread):
    """Execute a task in a new thread while blocking the parent widget."""

    def __init__(self, parent: QWidget, task: Optional[Callable[_P, _T]] = None):
        super().__init__()
        self.spinner = WaitingSpinner(
            parent=parent,
            disable_parent_when_spinning=True,
            modality=Qt.WindowModality.ApplicationModal,
            color=QApplication.palette().color(QPalette.ColorRole.Highlight),
        )
        self.finished.connect(self._on_finished)
        self._task = task
        self.on_finished: Optional[Callable[_T, ...]] = None
        self._result: Optional[_T] = None

    @property
    def task(self):
        return self._task

    @task.setter
    def task(self, task: Callable):
        self._task = task

    def run(self):
        self._result = self._task()

    def start(
        self, priority: QThread.Priority = QThread.Priority.NormalPriority
    ) -> None:
        self.wait()
        self.spinner.start()
        if self._task is None:
            raise ValueError("No task was defined for the waiting thread")
        super().start(priority)

    def _on_finished(self):
        self.spinner.stop()
        if self.on_finished is not None:
            self.on_finished(self._result)
            self.on_finished = None
            self._result = None


def create_on_close_message_box(parent: Optional[QWidget]) -> QMessageBox:
    message_box = QMessageBox(parent)
    message_box.setWindowTitle("Caqtus")
    message_box.setText("A sequence is still running.")
    message_box.setInformativeText("Do you want to interrupt it?")
    message_box.setStandardButtons(
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel
    )
    message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
    message_box.setIcon(QMessageBox.Icon.Question)
    return message_box
