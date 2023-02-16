import datetime
import logging
import shutil
import time
from copy import deepcopy
from functools import partial
from logging.handlers import QueueListener
from multiprocessing.managers import BaseManager
from pathlib import Path
from threading import Thread

from PyQt6 import QtCore
from PyQt6.QtCore import QSettings, QModelIndex, Qt, QTimer
from PyQt6.QtGui import (
    QIcon,
    QColor,
    QPalette,
    QFileSystemModel,
    QAction,
    QCloseEvent,
    QPainter,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QStyleOptionViewItem,
    QStyleOptionProgressBar,
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QMenu,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QTextBrowser,
)

from experiment.configuration import ExperimentConfig, get_config_path
from experiment_manager import ExperimentManager
from experiment.session import ExperimentSessionMaker
from sequence.configuration import (
    ShotConfiguration,
    SequenceConfig,
    SequenceSteps,
    ExecuteShot,
)
from sequence.runtime import Sequence, State
from .config_editor import ConfigEditor
from .experiment_viewer_ui import Ui_MainWindow
from .sequence_hierarchy_model import (
    SequenceHierarchyModel,
    SequenceStats,
    SequenceHierarchyItem,
)
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


def save_experiment_config(experiment_config: ExperimentConfig, path: Path):
    if path.exists():
        shutil.copyfile(path, f"{path}.old")

    yaml = experiment_config.to_yaml()
    with open(path, "w") as f:
        f.write(yaml)


class ExperimentViewer(QMainWindow, Ui_MainWindow):
    """Main window of the application

    It contains a file explorer to navigate the sequences and when clicking on a
    sequence, opens it in a dockable widget.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")

        self.setupUi(self)

        # restore window geometry from last session
        self.restoreState(self.ui_settings.value(f"{__name__}/state", self.saveState()))
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.action_edit_config.triggered.connect(self.edit_config)
        with open(get_config_path(), "r") as file:
            self.experiment_config = ExperimentConfig.from_yaml(file.read())
        self._experiment_session_maker = ExperimentSessionMaker(
            self.experiment_config.database_url
        )
        self.model = SequenceHierarchyModel(
            session_maker=self._experiment_session_maker
        )
        self.sequences_view.setModel(self.model)

        # special delegate that show progress bar
        delegate = SequenceDelegate(self.sequences_view)
        self.sequences_view.setItemDelegateForColumn(1, delegate)

        # context menu that let manage a sequence/folder
        self.sequences_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sequences_view.customContextMenuRequested.connect(self.show_context_menu)
        self.sequences_view.doubleClicked.connect(self.sequence_view_double_clicked)

        # refresh the view to update the info in real time
        self.view_update_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
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
        # noinspection PyUnresolvedReferences
        self.experiment_manager: ExperimentManager = (
            self.experiment_process_manager.ExperimentManager()
        )
        self.logs_listener = QueueListener(
            self.experiment_process_manager.get_logs_queue(), self.logs_handler
        )
        self.logs_listener.start()

    def sequence_view_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            return
        if path := self.model.get_path(index):
            sequence_widget = SequenceWidget(
                Sequence(path),
                deepcopy(self.experiment_config),
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
                    interrupt_sequence_action.setEnabled(False)
                    # interrupt_sequence_action.triggered.connect(
                    #     lambda _: self.experiment_manager.interrupt_sequence()
                    # )
                else:
                    clear_sequence_action = QAction("Remove data")
                    menu.addAction(clear_sequence_action)
                    # noinspection PyUnresolvedReferences
                    clear_sequence_action.triggered.connect(
                        partial(self.revert_to_draft, index)
                    )

                duplicate_sequence_action = QAction("Duplicate")
                menu.addAction(duplicate_sequence_action)
                duplicate_sequence_action.setEnabled(False)
                # duplicate_sequence_action.triggered.connect(
                #     partial(self.model.duplicate_sequence, index)
                # )
            else:  # index is folder
                can_create = True
        else:
            can_create = True  # can create in the root level
        if can_create:
            new_menu = QMenu("New...")
            menu.addMenu(new_menu)

            create_folder_action = QAction("folder")
            new_menu.addAction(create_folder_action)
            # noinspection PyUnresolvedReferences
            create_folder_action.triggered.connect(
                partial(self.create_new_folder, index)
            )

            create_sequence_action = QAction("sequence")
            new_menu.addAction(create_sequence_action)
            # noinspection PyUnresolvedReferences
            create_sequence_action.triggered.connect(
                partial(self.create_new_sequence, index)
            )

        if index.isValid() and is_deletable:
            delete_action = QAction("Delete")
            menu.addAction(delete_action)
            # noinspection PyUnresolvedReferences
            delete_action.triggered.connect(partial(self.delete, index))

        menu.exec(self.sequences_view.mapToGlobal(position))

    def start_sequence(self, index: QModelIndex):
        sequence_path = self.model.get_path(index)
        if sequence_path:
            with self._experiment_session_maker() as session:
                current_experiment_config = session.get_current_experiment_config_name()
            self.experiment_manager.start_sequence(
                current_experiment_config,
                sequence_path,
                self._experiment_session_maker
            )

    def create_new_folder(self, index: QModelIndex):
        if index.isValid():
            item: SequenceHierarchyItem = index.internalPointer()
            path = item.path
        else:
            path = "root"
        text, ok = QInputDialog().getText(
            None,
            f"New folder in {path}...",
            "Folder name:",
            QLineEdit.EchoMode.Normal,
            "new_folder",
        )
        if ok and text:
            self.model.create_new_folder(index, text)

    def create_new_sequence(self, index: QModelIndex):
        if index.isValid():
            item: SequenceHierarchyItem = index.internalPointer()
            path = item.path
        else:
            path = "root"
        text, ok = QInputDialog().getText(
            None,
            f"New sequence in {path}...",
            "Sequence name:",
            QLineEdit.EchoMode.Normal,
            "new_sequence",
        )
        if ok and text:
            self.model.create_new_sequence(index, text)

    def delete(self, index: QModelIndex):
        if index.isValid():
            item: "SequenceHierarchyItem" = index.internalPointer()
            path = str(item.sequence_path)
            message = (
                f'You are about to delete the path "{path}".\n'
                "All data inside will be irremediably lost."
            )
            if self.exec_confirmation_message_box(message):
                self.model.delete(index)

    def edit_config(self):
        """Open the experiment config editor then propagate the changes done"""

        editor = ConfigEditor(self.experiment_config)
        editor.exec()
        self.experiment_config = editor.get_config()
        save_experiment_config(self.experiment_config, get_config_path())
        self.update_experiment_config(self.experiment_config)

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.model.setRootPath(str(self.experiment_config.data_path))
        self.sequences_view.setRootIndex(
            self.model.index(str(self.experiment_config.data_path))
        )
        for sequence_widget in self.findChildren(SequenceWidget):
            sequence_widget: SequenceWidget
            logger.debug(sequence_widget.update_experiment_config(new_config))

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
        self.logs_listener.stop()
        super().closeEvent(event)

    def revert_to_draft(self, index: QModelIndex):
        """Remove all data files from a sequence"""

        if index.isValid():
            item: "SequenceHierarchyItem" = index.internalPointer()
            path = str(item.sequence_path)
            message = (
                f'You are about to revert the sequence "{path}" to draft.\n'
                "All associated data will be irremediably lost."
            )
            if self.exec_confirmation_message_box(message):
                self.model.revert_to_draft(index)

    def exec_confirmation_message_box(self, message: str) -> bool:
        """Show a popup box to ask if the sequence data should be erased"""
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
        elif result == QMessageBox.StandardButton.Yes:
            return True


class SequenceViewerModel(QFileSystemModel):
    """Model for sequence explorer"""

    # TODO: remove this class

    def __init__(self, data_root: Path, *args, **kwargs):
        self.sequence_watcher = SequenceFolderWatcher(data_root)
        logger.debug(self.sequence_watcher.data_folder)
        super().__init__(*args, **kwargs)
        self.setRootPath(str(data_root))

    def hasChildren(self, parent: QModelIndex = ...) -> bool:
        if self.is_sequence_folder(parent):
            return False
        return super().hasChildren(parent)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if self.is_sequence_folder(parent):
            return 0
        return super().rowCount(parent)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return super().columnCount(parent) + 2

    def filePath(self, index: QModelIndex) -> str:
        path = super().filePath(index)
        return normalize_path(path)

    def data(self, index: QModelIndex, role: int = ...):
        if self.is_sequence_folder(index):
            sequence = self.get_sequence(index)
            if index.column() == 4 and role == Qt.ItemDataRole.DisplayRole:
                return sequence
            elif index.column() == 5 and role == Qt.ItemDataRole.DisplayRole:
                if (
                    sequence.state == SequenceState.DRAFT
                    or sequence.state == SequenceState.UNTRUSTED
                    or sequence.state == SequenceState.PREPARING
                ):
                    return ""
                else:
                    duration = datetime.timedelta(
                        seconds=round(sequence.duration.total_seconds())
                    )
                    if sequence.state == SequenceState.FINISHED:
                        return f"{duration}"
                    else:
                        if sequence.remaining_duration == "unknown":
                            return ""
                        remaining_duration = datetime.timedelta(
                            seconds=round(sequence.remaining_duration.total_seconds())
                        )
                        return f"{duration}/{remaining_duration}"
            elif role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
                return QIcon(":/icons/sequence")
        return super().data(index, role)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            if section == 4:
                return "Status"
            elif section == 5:
                return "Duration"
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.isValid():
            flags |= Qt.ItemFlag.ItemIsDragEnabled
            file_info = self.fileInfo(index)
            if file_info.isDir() and not self.is_sequence_folder(index):
                flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def is_sequence_folder(self, parent: QModelIndex) -> bool:
        path = Path(self.filePath(parent))
        return self.sequence_watcher.is_sequence_folder(path)

    def fileIcon(self, index: QModelIndex) -> QIcon:
        if self.is_sequence_folder(index):
            return QIcon(":/icons/sequence")
        else:
            return super().fileIcon(index)

    def move_to_trash(self, index: QModelIndex):
        path = Path(self.filePath(index))
        Thread(target=lambda: shutil.rmtree(path)).start()

    def create_new_sequence(self, index: QModelIndex):
        path = Path(self.rootPath()) / self.fileName(index)
        text, ok = QInputDialog().getText(
            None,
            f"New sequence in {path}...",
            "Sequence name:",
            QLineEdit.EchoMode.Normal,
            "new_sequence",
        )
        if ok and text:
            new_sequence_path = path / text
            # noinspection PyBroadException
            try:
                config = SequenceConfig(
                    program=SequenceSteps(children=[ExecuteShot(name="shot")]),
                    shot_configurations={"shot": ShotConfiguration()},
                )
                Sequence.create_new_sequence(new_sequence_path, config)
            except Exception:
                logger.error(
                    f"Could not create new sequence '{new_sequence_path}'",
                    exc_info=True,
                )

    def create_new_folder(self, index: QModelIndex):
        path = Path(self.rootPath()) / self.fileName(index)
        text, ok = QInputDialog().getText(
            None,
            f"New folder in {path}...",
            "Folder name:",
            QLineEdit.EchoMode.Normal,
            "new_folder",
        )
        if ok and text:
            new_folder_path = path / text
            try:
                new_folder_path.mkdir(parents=True)
            except:
                logger.error(
                    f"Could not create new folder '{new_folder_path}'",
                    exc_info=True,
                )

    def duplicate_sequence(self, index: QModelIndex):
        path = Path(self.filePath(index)).relative_to(self.rootPath())
        text, ok = QInputDialog().getText(
            None,
            f"Duplicate sequence {path}",
            "New sequence name:",
            QLineEdit.EchoMode.Normal,
            str(path),
        )
        if ok and text:
            new_sequence_path = Path(self.rootPath()) / text
            # noinspection PyBroadException
            try:
                src_sequence = Sequence(Path(self.filePath(index)))
                src_config = src_sequence.config
                Sequence.create_new_sequence(new_sequence_path, src_config)
            except Exception:
                logger.error(
                    f"Could not create new sequence '{new_sequence_path}'",
                    exc_info=True,
                )

    def revert_to_draft(self, index: QModelIndex):
        """Remove all data files from a sequence"""
        if self.is_sequence_folder(index):
            sequence = self.get_sequence(index)
            Thread(target=sequence.revert_to_draft).start()

    def get_sequence(self, index: QModelIndex) -> "Sequence":
        path = Path(self.filePath(index))
        if self.is_sequence_folder(index):
            sequence = self.sequence_watcher.get_sequence(path, read_only=False)
            return sequence
        else:
            raise RuntimeError(f"Folder {path} is not a sequence")


class SequenceDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        # noinspection PyTypeChecker
        model: SequenceViewerModel = index.model()
        sequence_stats: SequenceStats = model.data(index, Qt.ItemDataRole.DisplayRole)
        if sequence_stats:
            opt = QStyleOptionProgressBar()
            opt.rect = option.rect
            opt.minimum = 0
            opt.maximum = 100
            opt.textVisible = True
            state = sequence_stats["state"]
            if state == State.DRAFT:
                opt.progress = 0
                opt.text = "draft"
            elif state == State.PREPARING:
                opt.progress = 0
                opt.text = "preparing"
            else:
                total = sequence_stats["total_number_shots"]
                if total:
                    opt.progress = sequence_stats["number_completed_shots"]
                    opt.maximum = total
                else:
                    if state == State.RUNNING:  # filled bar with sliding reflects
                        opt.progress = 0
                        opt.maximum = 0
                    else:  # filled bar
                        opt.progress = 1
                        opt.maximum = 1

                if state == State.RUNNING:
                    opt.text = "running"
                elif state == State.INTERRUPTED:
                    opt.text = "interrupted"
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(166, 138, 13)
                    )
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(92, 79, 23))
                elif state == State.FINISHED:
                    opt.text = f"finished"
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(98, 151, 85)
                    )
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
                elif state == State.CRASHED:
                    opt.text = "crashed"
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(119, 46, 44))
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(240, 82, 79)
                    )
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_ProgressBar, opt, painter
            )
        else:
            super().paint(painter, option, index)
