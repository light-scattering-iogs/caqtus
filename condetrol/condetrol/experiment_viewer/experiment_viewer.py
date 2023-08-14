import logging
import time
from functools import partial
from logging.handlers import QueueListener
from multiprocessing.managers import BaseManager
from typing import Callable, Optional

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
)
from waiting_widget.spinner import WaitingSpinner

from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker
from experiment_control.manager import ExperimentManager
from sequence.runtime import Sequence, State
from sequence_hierarchy import EditableSequenceHierarchyModel, SequenceHierarchyDelegate
from .config_editor import ConfigEditor
from .experiment_viewer_ui import Ui_MainWindow
from .sequence_widget import SequenceWidget

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


ExperimentProcessManager.register("ExperimentManager")
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

        with self._experiment_session_maker() as session:
            self._experiment_config = (
                session.experiment_configs.get_current_experiment_config()
            )
            self._experiment_config_name = (
                session.experiment_configs.get_current_experiment_config_name()
            )

        self.setupUi(self)

        # restore window geometry from last session
        self.restoreState(self.ui_settings.value(f"{__name__}/state", self.saveState()))
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.action_edit_config.triggered.connect(self.edit_config)

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
        self.experiment_manager: ExperimentManager = (
            self.experiment_process_manager.ExperimentManager()  # type: ignore
        )
        self.logs_listener = QueueListener(
            self.experiment_process_manager.get_logs_queue(), self.logs_handler  # type: ignore
        )
        self.logs_listener.start()
        self.worker = BlockingThread(self)

    def sequence_view_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        if path := self.model.get_path(index):
            sequence_widget = SequenceWidget(
                Sequence(path),
                self.get_current_experiment_config(),
                self._experiment_session_maker,
            )
            self.dock_widget.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, sequence_widget
            )

    def get_current_experiment_config(self) -> ExperimentConfig:
        with self._experiment_session_maker() as session:
            if (
                self._experiment_config_name
                == session.experiment_configs.get_current_experiment_config_name()
            ):
                return self._experiment_config
            else:
                experiment_config = (
                    session.experiment_configs.get_current_experiment_config()
                )
                if experiment_config is None:
                    raise ValueError("No experiment config was defined")

                self._experiment_config_name = (
                    session.experiment_configs.get_current_experiment_config_name()
                )
                self._experiment_config = experiment_config
            return self._experiment_config

    def show_context_menu(self, position):
        index = self.sequences_view.indexAt(position)

        menu = QMenu(self.sequences_view)

        is_deletable = True
        can_create = False

        if index.isValid():
            if self.model.is_sequence(index):
                stats = self.model.get_sequence_stats(index)
                state = stats["state"]
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
                        lambda _: self.experiment_manager.interrupt_sequence()
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
                current_experiment_config = (
                    session.experiment_configs.get_current_experiment_config_name()
                )
            self.experiment_manager.start_sequence(
                current_experiment_config, sequence_path, self._experiment_session_maker
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

    def edit_config(self):
        """Open the experiment config editor then propagate the changes done"""

        current_config = self.get_current_experiment_config()

        editor = ConfigEditor(current_config)
        editor.exec()
        new_experiment_config = editor.get_config()
        if current_config != new_experiment_config:
            with self._experiment_session_maker() as session:
                new_name = session.experiment_configs.add_experiment_config(
                    new_experiment_config
                )
                session.experiment_configs.set_current_experiment_config(
                    new_name
                )
            logger.info(f"Experiment config updated to {new_name}")
        self.update_experiment_config(new_experiment_config)

    def update_experiment_config(self, new_config: ExperimentConfig):
        for sequence_widget in self.findChildren(SequenceWidget):
            sequence_widget.update_experiment_config(new_config)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.experiment_manager.is_running():
            message_box = QMessageBox(self)
            message_box.setWindowTitle("Caqtus")
            message_box.setText("A sequence is still running.")
            message_box.setInformativeText("Do you want to interrupt it?")
            message_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            message_box.setIcon(QMessageBox.Icon.Question)
            result = message_box.exec()
            if result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif result == QMessageBox.StandardButton.Yes:
                self.experiment_manager.interrupt_sequence()
                while self.experiment_manager.is_running():
                    time.sleep(0.1)
        state = self.saveState()
        self.ui_settings.setValue(f"{__name__}/state", state)
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)
        # The following line waits to have all logs before closing, but for some reason, it blocks forever.
        # It is commented for now, but can cause some logs to be lost.
        # self.logs_listener.stop()
        self.model.on_destroy()
        super().closeEvent(event)

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


class BlockingThread(QThread):
    """Execute a task in a new thread while blocking the parent widget."""

    def __init__(self, parent: QWidget, task: Optional[Callable] = None):
        super().__init__()
        self.spinner = WaitingSpinner(
            parent=parent,
            disable_parent_when_spinning=True,
            modality=Qt.WindowModality.ApplicationModal,
            color=QApplication.palette().color(QPalette.ColorRole.Highlight),
        )
        self.finished.connect(self.spinner.stop)
        self._task = task

    @property
    def task(self):
        return self._task

    @task.setter
    def task(self, task: Callable):
        self._task = task

    def run(self):
        self._task()

    def start(self, priority: QThread.Priority = QThread.Priority.HighPriority) -> None:
        self.wait()
        self.spinner.start()
        if self._task is None:
            raise ValueError("No task was defined for the waiting thread")
        super().start(priority)
