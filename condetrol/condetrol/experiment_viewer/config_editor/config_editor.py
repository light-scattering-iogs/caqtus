import logging
from pathlib import Path

from PyQt5 import QtGui
from PyQt5.QtCore import (
    QSettings,
    QModelIndex,
    Qt,
    QAbstractListModel,
    QFileSystemWatcher,
    QMimeData,
)
from PyQt5.QtWidgets import (
    QDialog,
    QDataWidgetMapper,
    QWidget,
    QFormLayout,
    QTreeWidgetItem,
    QLabel,
    QTreeView,
    QAbstractItemView,
    QMenu,
    QAction,
)

from condetrol.utils import log_error
from condetrol.widgets import FolderWidget, SaveFileWidget, SettingsDelegate
from experiment_config import ExperimentConfig, get_config_path
from expression import Expression
from sequence import Step, VariableDeclaration, ExecuteShot
from settings_model import YAMLSerializable
from .config_editor_ui import Ui_config_editor
from ..steps_editor import StepsModel, StepDelegate

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ConfigModel(QAbstractListModel):
    def __init__(self, config: ExperimentConfig, save_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: ExperimentConfig = config
        self._save_path = save_path
        self._config_watcher = QFileSystemWatcher()
        self._config_watcher.addPath(str(self._save_path))
        self._config_watcher.fileChanged.connect(self.config_changed)

    def config_changed(self, path):
        self.beginResetModel()
        self._config: ExperimentConfig = load_config(Path(path))
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.row() == 0:
                return str(self._config.data_path)

    # noinspection PyTypeChecker
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.isValid():
            return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled

    @log_error(logger)
    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        change = False
        if role == Qt.ItemDataRole.EditRole:
            if index.row() == 0:
                self._config.data_path = value
                change = True
        if change:
            if not self._save_path.parent.exists():
                self._save_path.parent.mkdir(exist_ok=True, parents=True)
            with open(self._save_path, "w") as file:
                YAMLSerializable.dump(self._config, file)

        return change


class SystemSettingsEditor(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.config_path = get_config_path()
        self.config = load_config(self.config_path)

        self.config_path_widget = SaveFileWidget(
            self.config_path, "Edit config path...", "config (*.yaml)"
        )
        self.layout.insertRow(0, "Config path", self.config_path_widget)
        self.config_path_widget.setEnabled(False)

        self.data_path_widget = FolderWidget(
            "Edit data path...",
        )
        self.layout.insertRow(1, "Data path", self.data_path_widget)

        self.config_model = ConfigModel(self.config, self.config_path)
        self.mapper = QDataWidgetMapper()
        self.mapper.setOrientation(Qt.Orientation.Vertical)
        self.mapper.setModel(self.config_model)
        self.mapper.addMapping(self.data_path_widget, 0)
        self.mapper.setItemDelegate(SettingsDelegate())
        self.mapper.toFirst()

        self.data_path_widget.folder_edited.connect(self.mapper.submit)


class SequenceHeaderModel(StepsModel):
    def __init__(self, config_path: Path):
        super().__init__()
        self._config: ExperimentConfig = YAMLSerializable.load(config_path)
        self._config_path = config_path

        self._config_watcher = QFileSystemWatcher()
        self._config_watcher.addPath(str(config_path))
        self._config_watcher.fileChanged.connect(self.config_changed)

    def config_changed(self, path):
        self.beginResetModel()
        self._config: ExperimentConfig = load_config(Path(path))
        self.endResetModel()

    @property
    def root(self) -> Step:
        return self._config.header

    def save_config(self) -> bool:
        self._config_watcher.blockSignals(True)
        try:
            YAMLSerializable.dump(self._config, self._config_path)
        finally:
            self._config_watcher.blockSignals(False)
        return True

    def setData(self, index: QModelIndex, values: dict[str], role: int = ...) -> bool:
        if result := super().setData(index, values, role):
            self.save_config()
        return result

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = super().flags(index)
            flags |= Qt.ItemFlag.ItemIsEditable
            if not isinstance(
                self.data(index, Qt.ItemDataRole.DisplayRole),
                (VariableDeclaration, ExecuteShot),
            ):
                flags |= Qt.ItemFlag.ItemIsDropEnabled
        else:
            flags = Qt.ItemFlag.NoItemFlags
        return flags

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if result := super().dropMimeData(data, action, row, column, parent):
            self.save_config()
        return result

    def insert_step(self, new_step: Step, index: QModelIndex):
        super().insert_step(new_step, index)
        self.save_config()

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        if result := super().removeRows(row, count, parent):
            self.save_config()
        return result

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if result := super().removeRow(row, parent):
            self.save_config()
        return result


class SequenceHeaderEditor(QTreeView):
    """Editor for the steps that are executed before each sequence

    Only allows to declare constants at the moment.
    """

    def __init__(self, config_path: Path):
        super().__init__()

        self.model = SequenceHeaderModel(config_path)
        self.setModel(self.model)
        delegate = StepDelegate()
        self.setItemDelegate(delegate)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setContentsMargins(0, 0, 0, 0)

        self.model.modelReset.connect(lambda: self.expandAll())
        self.expandAll()
        self.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.model.rowsInserted.connect(lambda _: self.expandAll())

        self.setItemsExpandable(False)

        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        index = self.indexAt(position)
        # noinspection PyTypeChecker

        menu = QMenu(self)

        add_menu = QMenu()
        add_menu.setTitle("Add...")
        menu.addMenu(add_menu)

        create_variable_action = QAction("constant")
        add_menu.addAction(create_variable_action)
        create_variable_action.triggered.connect(
            lambda: self.model.insert_step(
                VariableDeclaration(name="", expression=Expression()), index
            )
        )
        menu.exec(self.mapToGlobal(position))


def load_config(config_path: Path) -> ExperimentConfig:
    """Loads or creates the experiment config"""

    if config_path.exists():
        # noinspection PyBroadException
        try:
            with open(config_path, "r") as file:
                config = YAMLSerializable.load(file)
            if not isinstance(config, ExperimentConfig):
                raise TypeError(f"Config is not correct: {config}")
        except Exception:
            logger.warning(
                f"Unable to load {config_path}. Loading a default configuration"
                " instead.",
                exc_info=True,
            )
            config = ExperimentConfig()
    else:
        config = ExperimentConfig()
    return config


class ConfigEditor(QDialog, Ui_config_editor):
    @log_error(logger)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")
        self.setupUi(self)
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.d = {}
        self.d["system"] = (
            QTreeWidgetItem(self.category_tree, ["System"]),
            SystemSettingsEditor(),
        )
        self.d["system"][0].setSelected(True)
        self.d["constants"] = (
            QTreeWidgetItem(self.category_tree, ["Constants"]),
            SequenceHeaderEditor(get_config_path()),
        )
        self.d["devices"] = (QTreeWidgetItem(self.category_tree, ["Devices"]), None)
        self.d[r"devices\spincore"] = (
            QTreeWidgetItem(self.d["devices"][0], ["Spincore pulseblaster"]),
            QLabel("Spincore"),
        )
        self.d[r"devices\ni6738"] = (
            QTreeWidgetItem(self.d["devices"][0], ["NI6738"]),
            QLabel("NI6738"),
        )

        for w in self.d.values():
            if w[1] is not None:
                self.stack_widget.addWidget(w[1])

        self.category_tree.currentItemChanged.connect(self.show_widget)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)
        super().closeEvent(a0)

    def show_widget(self, item: QTreeWidgetItem, _):
        for it, widget in self.d.values():
            if it == item and widget is not None:
                self.stack_widget.setCurrentWidget(widget)
                break
