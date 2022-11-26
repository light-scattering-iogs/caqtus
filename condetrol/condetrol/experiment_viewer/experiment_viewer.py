import datetime
import logging
import os
import shutil
import time
from functools import partial
from logging.handlers import QueueListener
from multiprocessing.managers import BaseManager
from pathlib import Path
from threading import Thread

import yaml
from PyQt5 import QtCore
from PyQt5.QtCore import QSettings, QModelIndex, Qt, QTimer
from PyQt5.QtGui import QIcon, QColor, QPalette
from PyQt5.QtWidgets import (
    QMainWindow,
    QFileSystemModel,
    QStyleOptionViewItem,
    QStyleOptionProgressBar,
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QMenu,
    QAction,
    QInputDialog,
    QLineEdit,
    QAbstractItemView,
    QMessageBox,
    QTextBrowser,
)
from qtpy import QtGui

from experiment_config import ExperimentConfig
from experiment_manager import ExperimentManager
from sequence import (
    SequenceStats,
    SequenceState,
    SequenceConfig,
    SequenceSteps,
    ExecuteShot,
)
from sequence.sequence import Sequence, SequenceFolderWatcher
from settings_model import YAMLSerializable
from sequence.shot import ShotConfiguration
from .config_editor import ConfigEditor
from .config_editor import get_config_path, load_config
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
    header = "<b>%(levelname)s</b> %(asctime)s - <a href=%(pathname)s:%(lineno)d>%(pathname)s:%(lineno)d</a>"

    FORMATS = {
        logging.DEBUG: f"<span style='color:grey;white-space: pre-wrap'>{header} %(message)s</span>",
        logging.INFO: f"<span style='color:white;white-space:pre-wrap'>{header} %(message)s</span>",
        logging.WARNING: f"<span style='color:yellow;white-space:pre-wrap'>{header} %(message)s</span>",
        logging.ERROR: f"<span style='color:red;white-space: pre-wrap'>{header} %(message)s</span>",
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

    def __init__(self, *args, **kwargs):
        logger.info(f"Started experiment viewer in process {os.getpid()}")
        super().__init__(*args, **kwargs)
        os.environ["QT_FILESYSTEMMODEL_WATCH_FILES"] = "1"

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")

        self.setupUi(self)
        # restore window geometry from last session
        self.restoreState(self.ui_settings.value(f"{__name__}/state", self.saveState()))
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.action_edit_config.triggered.connect(self.edit_config)
        self.experiment_config: ExperimentConfig = load_config(get_config_path())
        self.model = SequenceViewerModel(self.experiment_config.data_path)
        self.sequences_view.setModel(self.model)
        self.sequences_view.setRootIndex(
            self.model.index(str(self.experiment_config.data_path))
        )
        delegate = SequenceDelegate(self.sequences_view)
        self.sequences_view.setItemDelegateForColumn(4, delegate)
        self.sequences_view.setColumnHidden(1, True)
        self.sequences_view.setColumnHidden(2, True)
        self.sequences_view.setColumnHidden(3, True)
        # self.sequences_view.setColumnHidden(5, True)
        self.sequences_view.doubleClicked.connect(self.sequence_view_double_clicked)
        self.sequences_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sequences_view.customContextMenuRequested.connect(self.show_context_menu)
        self.sequences_view.setDragEnabled(True)
        self.sequences_view.setAcceptDrops(True)
        self.sequences_view.setDropIndicatorShown(True)
        self.sequences_view.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.sequences_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.sequences_view.setDragDropOverwriteMode(False)

        self.view_update_timer = QTimer(self)
        self.view_update_timer.timeout.connect(self.sequences_view.update)
        self.view_update_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.view_update_timer.start(500)

        self.dock_widget = QMainWindow()
        self.setCentralWidget(self.dock_widget)

        self.logs_handler = TextBrowserEditLogger()
        # self.logs_widget.setPlainText("test\n" * 50)
        self.logs_dock.setWidget(self.logs_handler.widget)
        self.logs_handler.setFormatter(CustomFormatter())
        # self.logs_handler.setFormatter(
        #     logging.Formatter(
        #         "<b>%(levelname)s</b> %(asctime)s (%(module)s, %(funcName)s): %(message)s"
        #     )
        # )
        logging.getLogger().addHandler(self.logs_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        # logger.debug("ty")
        # self.logs_widget.setMinimumHeight(0)

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
        # noinspection PyTypeChecker
        model: SequenceViewerModel = index.model()
        if model.is_sequence_folder(index):
            sequence_widget = SequenceWidget(
                Path(model.filePath(index)), get_config_path()
            )
            self.dock_widget.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, sequence_widget
            )

    def start_sequence(self, path: Path):
        config = YAMLSerializable.dump(self.experiment_config)
        self.experiment_manager.start_sequence(
            config, path.relative_to(self.experiment_config.data_path)
        )

    def show_context_menu(self, position):
        index = self.sequences_view.indexAt(position)

        menu = QMenu(self.sequences_view)

        is_deletable = True

        if self.model.is_sequence_folder(index):
            stats = self.model.data(index, Qt.ItemDataRole.DisplayRole).stats
            if stats.state == SequenceState.RUNNING:
                is_deletable = False
                interrupt_sequence_action = QAction("Interrupt")
                menu.addAction(interrupt_sequence_action)
                interrupt_sequence_action.triggered.connect(
                    lambda _: self.experiment_manager.interrupt_sequence()
                ),
            if stats.state == SequenceState.DRAFT:
                start_sequence_action = QAction("Start")
                menu.addAction(start_sequence_action)
                start_sequence_action.triggered.connect(
                    lambda _: self.start_sequence(Path(self.model.filePath(index))),
                )
            duplicate_sequence_action = QAction("Duplicate")
            menu.addAction(duplicate_sequence_action)
            duplicate_sequence_action.triggered.connect(
                partial(self.model.duplicate_sequence, index)
            )

            if (
                stats.state != SequenceState.RUNNING
                and stats.state != SequenceState.DRAFT
            ):
                clear_sequence_action = QAction("Remove data")
                menu.addAction(clear_sequence_action)
                clear_sequence_action.triggered.connect(
                    partial(self.model.revert_to_draft, index)
                )

        else:
            new_menu = QMenu("New...")
            menu.addMenu(new_menu)

            create_folder_action = QAction("folder")
            new_menu.addAction(create_folder_action)
            create_folder_action.triggered.connect(
                partial(self.model.create_new_folder, index)
            )

            create_sequence_action = QAction("sequence")
            new_menu.addAction(create_sequence_action)
            create_sequence_action.triggered.connect(
                partial(self.model.create_new_sequence, index)
            )

        if index.isValid() and is_deletable:
            delete_action = QAction("Delete")
            menu.addAction(delete_action)
            delete_action.triggered.connect(partial(self.model.move_to_trash, index))

        menu.exec(self.sequences_view.mapToGlobal(position))

    def edit_config(self):
        """Open the experiment config editor"""
        editor = ConfigEditor()
        editor.exec()
        self.update_experiment_config(load_config(get_config_path()))

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.experiment_config = new_config
        self.model.setRootPath(str(self.experiment_config.data_path))
        self.sequences_view.setRootIndex(
            self.model.index(str(self.experiment_config.data_path))
        )
        for sequence_widget in self.findChildren(SequenceWidget):
            sequence_widget: SequenceWidget
            logger.debug(sequence_widget.update_experiment_config(new_config))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.experiment_manager.is_running():
            message_box = QMessageBox(self)
            message_box.setWindowTitle("Caqtus")
            message_box.setText("A sequence is still running.")
            message_box.setInformativeText("Do you want to interrupt it?")
            message_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            message_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            message_box.setIcon(QMessageBox.Question)
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


class SequenceViewerModel(QFileSystemModel):
    """Model for sequence explorer"""

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
            sequence = self.sequence_watcher.get_sequence(Path(self.filePath(index)))
            if index.column() == 4 and role == Qt.ItemDataRole.DisplayRole:
                return sequence
            elif index.column() == 5 and role == Qt.ItemDataRole.DisplayRole:
                if sequence.state == SequenceState.DRAFT:
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
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

    def fileIcon(self, index: QModelIndex) -> QtGui.QIcon:
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
            try:
                new_sequence_path.mkdir()
                config = SequenceConfig(
                    program=SequenceSteps(children=[ExecuteShot(name="shot")]),
                    shot_configurations={"shot": ShotConfiguration()},
                )
                YAMLSerializable.dump(
                    config, new_sequence_path / "sequence_config.yaml"
                )
                stats = SequenceStats()
                YAMLSerializable.dump(stats, new_sequence_path / "sequence_state.yaml")
            except:
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
            try:
                new_sequence_path.mkdir(parents=True)
                stats = SequenceStats()
                with open(new_sequence_path / "sequence_state.yaml", "w") as file:
                    file.write(yaml.safe_dump(stats))
                shutil.copy(
                    Path(self.filePath(index)) / "sequence_config.yaml",
                    new_sequence_path / "sequence_config.yaml",
                )

            except:
                logger.error(
                    f"Could not create new sequence '{new_sequence_path}'",
                    exc_info=True,
                )

    def revert_to_draft(self, index: QModelIndex) -> bool:
        sequence_reverted = False
        if self.is_sequence_folder(index):
            path = Path(self.filePath(index))
            state = self.sequence_watcher.get_sequence(path).state
            if state != SequenceState.DRAFT and state != SequenceState.RUNNING:
                stats = SequenceStats()
                YAMLSerializable.dump(stats, path / "sequence_state.yaml")
                os.remove(path / "experiment_config.yaml")

                def target():
                    files = (file for file in path.iterdir() if file.is_file())
                    for file in files:
                        if file.suffix == ".hdf5":
                            os.remove(file)

                Thread(target=target).start()

        return sequence_reverted


class SequenceDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        # noinspection PyTypeChecker
        model: SequenceViewerModel = index.model()
        if model.is_sequence_folder(index):
            sequence: Sequence = model.data(index, Qt.ItemDataRole.DisplayRole)
            opt = QStyleOptionProgressBar()
            opt.rect = option.rect
            opt.minimum = 0
            opt.maximum = 100
            opt.textVisible = True
            stats = sequence.stats
            if stats.state == SequenceState.DRAFT:
                opt.progress = 0
                opt.text = "draft"
            else:
                opt.maximum = sequence.total_number_shots
                opt.progress = sequence.number_completed_shots

                if stats.state == SequenceState.RUNNING:
                    opt.text = "running"
                elif stats.state == SequenceState.INTERRUPTED:
                    opt.text = "interrupted"
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(166, 138, 13)
                    )
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(92, 79, 23))
                elif stats.state == SequenceState.FINISHED:
                    opt.text = f"finished"
                    opt.palette.setColor(
                        QPalette.ColorRole.Highlight, QColor(98, 151, 85)
                    )
                    opt.palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
                elif stats.state == SequenceState.CRASHED:
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


def normalize_path(path: str):
    path = os.path.normpath(path)
    drive, relative_path = os.path.splitdrive(path)
    relative_path = relative_path.removeprefix("\\")

    return os.path.join(drive, relative_path)
