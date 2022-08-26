import datetime
import logging
import os
from pathlib import Path

import yaml
from PyQt5.QtCore import QSettings, QModelIndex, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow,
    QFileSystemModel,
    QStyleOptionViewItem,
    QStyleOptionProgressBar,
    QApplication,
    QStyle,
    QStyledItemDelegate,
)
from experiment_config import ExperimentConfig
from qtpy import QtGui
from sequence import SequenceStats, SequenceState

from .config_editor import ConfigEditor
from .config_editor import get_config_path, load_config
from .experiment_viewer_ui import Ui_MainWindow
from .sequence_widget import SequenceWidget

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentViewer(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.environ["QT_FILESYSTEMMODEL_WATCH_FILES"] = "1"

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")

        self.setupUi(self)
        self.restoreState(self.ui_settings.value(f"{__name__}/state", self.saveState()))
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.action_edit_config.triggered.connect(self.edit_config)
        self.config: ExperimentConfig = load_config(get_config_path())
        today_folder = self.config.data_path / datetime.datetime.now().strftime(
            "%d-%m-%Y"
        )
        today_folder.mkdir(parents=True, exist_ok=True)
        self.model = SequenceViewerModel(self.config.data_path)
        self.sequences_view.setModel(self.model)
        self.sequences_view.setRootIndex(self.model.index(str(self.config.data_path)))
        delegate = SequenceDelegate(self.sequences_view)
        self.sequences_view.setItemDelegateForColumn(4, delegate)
        self.sequences_view.setColumnHidden(1, True)
        self.sequences_view.setColumnHidden(2, True)
        self.sequences_view.setColumnHidden(3, True)
        self.sequences_view.doubleClicked.connect(self.sequence_view_double_clicked)

        self.setCentralWidget(None)

    def sequence_view_double_clicked(self, index: QModelIndex):
        # noinspection PyTypeChecker
        model: SequenceViewerModel = index.model()
        if model.is_sequence_folder(index):
            sequence_widget = SequenceWidget(Path(model.filePath(index)))
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, sequence_widget)

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


class SequenceDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        # noinspection PyTypeChecker
        model: SequenceViewerModel = index.model()
        if model.is_sequence_folder(index):
            opt = QStyleOptionProgressBar()
            opt.rect = option.rect
            opt.minimum = 0
            opt.maximum = 1
            stats: SequenceStats = model.data(index, Qt.ItemDataRole.DisplayRole)
            if stats.state == SequenceState.DRAFT:
                opt.progress = 0
                opt.text = "draft"
                opt.textVisible = True
            QApplication.style().drawControl(
                QStyle.ControlElement.CE_ProgressBar, opt, painter
            )


class SequenceViewerModel(QFileSystemModel):
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
        return super().columnCount(parent) + 1

    def data(self, index: QModelIndex, role: int = ...):
        if self.is_sequence_folder(index):
            if index.column() == 4 and role == Qt.ItemDataRole.DisplayRole:
                path = Path(self.filePath(index)) / "sequence_state.yaml"
                with open(path) as file:
                    result: SequenceStats = yaml.safe_load(file)
                    return result
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
        return super().headerData(section, orientation, role)

    def is_sequence_folder(self, parent: QModelIndex) -> bool:
        path = Path(self.filePath(parent))
        if (path / "sequence_state.yaml").exists():
            return True
        return False

    def fileIcon(self, aindex: QModelIndex) -> QtGui.QIcon:
        if self.is_sequence_folder(aindex):
            return QIcon(":/icons/sequence")
        else:
            return super().fileIcon(aindex)
