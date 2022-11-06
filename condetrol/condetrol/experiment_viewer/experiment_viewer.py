import datetime
import logging
import os
import shutil
from functools import partial, lru_cache
from multiprocessing.managers import BaseManager
from pathlib import Path

import yaml
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
)
from qtpy import QtGui
from send2trash import send2trash

from experiment_config import ExperimentConfig
from experiment_manager import ExperimentManager
from sequence import (
    SequenceStats,
    SequenceState,
    SequenceConfig,
    SequenceSteps,
    ExecuteShot,
    Sequence,
)
from settings_model import YAMLSerializable
from shot import ShotConfiguration
from .config_editor import ConfigEditor
from .config_editor import get_config_path, load_config
from .experiment_viewer_ui import Ui_MainWindow
from .sequence_widget import SequenceWidget

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


ExperimentProcessManager.register("ExperimentManager")


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
        self.config: ExperimentConfig = load_config(get_config_path())
        self.model = SequenceViewerModel(self.config.data_path)
        self.sequences_view.setModel(self.model)
        self.sequences_view.setRootIndex(self.model.index(str(self.config.data_path)))
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

        self.setCentralWidget(None)

        self.experiment_process_manager = ExperimentProcessManager(
            address=("localhost", 60000), authkey=b"Deardear"
        )
        self.experiment_process_manager.connect()
        # noinspection PyUnresolvedReferences
        self.experiment_manager: ExperimentManager = (
            self.experiment_process_manager.ExperimentManager()
        )

    def sequence_view_double_clicked(self, index: QModelIndex):
        # noinspection PyTypeChecker
        model: SequenceViewerModel = index.model()
        if model.is_sequence_folder(index):
            sequence_widget = SequenceWidget(
                Path(model.filePath(index)), get_config_path()
            )
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, sequence_widget)

    def start_sequence(self, path: Path):
        config = YAMLSerializable.dump(self.config)
        self.experiment_manager.start_sequence(
            config, path.relative_to(self.config.data_path)
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

    @staticmethod
    def edit_config():
        editor = ConfigEditor()
        editor.exec()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        state = self.saveState()
        self.ui_settings.setValue(f"{__name__}/state", state)
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)
        super().closeEvent(a0)


@lru_cache(maxsize=128)
def get_sequence(path: Path):
    return Sequence(path, monitoring=True)


class SequenceViewerModel(QFileSystemModel):
    """Model for sequence explorer"""

    def __init__(self, data_root: Path, *args, **kwargs):
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

    def data(self, index: QModelIndex, role: int = ...):
        if self.is_sequence_folder(index):
            sequence = get_sequence(Path(self.filePath(index)))
            if index.column() == 4 and role == Qt.ItemDataRole.DisplayRole:
                return sequence
            elif index.column() == 5 and role == Qt.ItemDataRole.DisplayRole:
                if sequence.state == SequenceState.DRAFT:
                    return ""
                elif sequence.state == SequenceState.FINISHED:
                    start_time = sequence.stats.start_time
                    end_time = sequence.stats.stop_time
                    duration = datetime.timedelta(
                        seconds=int((end_time - start_time).total_seconds())
                    )
                    return str(duration)
                elif (
                    sequence.state == SequenceState.INTERRUPTED
                    or sequence.state == SequenceState.CRASHED
                ):
                    start_time = sequence.stats.start_time
                    end_time = sequence.stats.stop_time
                    duration = datetime.timedelta(
                        seconds=int((end_time - start_time).total_seconds())
                    )
                    return f"{duration}/--"
                elif sequence.state == SequenceState.RUNNING:
                    start_time = sequence.stats.start_time
                    end_time = datetime.datetime.now()
                    duration = datetime.timedelta(
                        seconds=int((end_time - start_time).total_seconds())
                    )
                    return f"{duration}/--"

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
        if (path / "sequence_state.yaml").exists():
            return True
        return False

    def fileIcon(self, index: QModelIndex) -> QtGui.QIcon:
        if self.is_sequence_folder(index):
            return QIcon(":/icons/sequence")
        else:
            return super().fileIcon(index)

    def move_to_trash(self, index: QModelIndex):
        path = Path(self.filePath(index))
        send2trash(path)

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
                    program=SequenceSteps(
                        children=[
                            ExecuteShot(name="shot", configuration=ShotConfiguration())
                        ]
                    )
                )
                with open(new_sequence_path / "sequence_config.yaml", "w") as file:
                    file.write(yaml.safe_dump(config))
                stats = SequenceStats()
                with open(new_sequence_path / "sequence_state.yaml", "w") as file:
                    file.write(yaml.safe_dump(stats))
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
            QLineEdit.Normal,
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
