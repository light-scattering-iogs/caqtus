import logging
from pathlib import Path

from PyQt5 import QtGui
from PyQt5.QtCore import (
    QSettings,
    QModelIndex,
    Qt,
    QAbstractListModel,
)
from PyQt5.QtWidgets import (
    QDialog,
    QDataWidgetMapper,
    QWidget,
    QFormLayout,
    QTreeWidgetItem,
    QLabel,
)
from appdirs import user_config_dir

from condetrol.utils import log_error
from condetrol.widgets import FolderWidget, SaveFileWidget, SettingsDelegate
from experiment_config import ExperimentConfig
from settings_model import YAMLSerializable
from .config_editor_ui import Ui_config_editor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ConfigModel(QAbstractListModel):
    def __init__(self, config: ExperimentConfig, save_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: ExperimentConfig = config
        self._save_path = save_path

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
    @log_error(logger)
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


def get_config_path() -> Path:
    ui_settings = QSettings("Caqtus", "ExperimentControl")
    config_folder = ui_settings.value(
        "experiment/config_path", user_config_dir("ExperimentControl", "Caqtus")
    )
    config_path = Path(config_folder) / "config.yaml"
    return config_path


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
            QLabel("Constants"),
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
