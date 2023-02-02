from typing import Optional

from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex
from PyQt6.QtWidgets import QFormLayout, QDataWidgetMapper, QWidget

from condetrol.widgets import FolderWidget, SaveFileWidget, SettingsDelegate
from experiment_config import ExperimentConfig, get_config_path
from ..config_settings_editor import ConfigSettingsEditor


class SystemSettingsEditor(ConfigSettingsEditor):
    """A widget that allow to edit the system settings

    This includes the path to store the config file and the path to store the experiment data.
    """

    def get_experiment_config(self) -> ExperimentConfig:
        return self.model.get_config()

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.config = experiment_config

        self.config_path_widget = SaveFileWidget(
            get_config_path(), "Edit config path...", "config (*.yaml)"
        )
        self.layout.insertRow(0, "Config path", self.config_path_widget)
        self.config_path_widget.setEnabled(False)

        self.data_path_widget = FolderWidget(
            "Edit data path...",
        )
        self.layout.insertRow(1, "Data path", self.data_path_widget)

        self.model = SystemSettingsModel(self.config)
        self.mapper = QDataWidgetMapper()
        self.mapper.setOrientation(Qt.Orientation.Vertical)
        self.mapper.setModel(self.model)
        self.mapper.addMapping(self.data_path_widget, 0)
        self.mapper.setItemDelegate(SettingsDelegate())
        self.mapper.toFirst()

        self.data_path_widget.folder_edited.connect(self.mapper.submit)


class SystemSettingsModel(QAbstractListModel):
    def __init__(self, config: ExperimentConfig):
        super().__init__()
        self._config: ExperimentConfig = config

    def get_config(self) -> ExperimentConfig:
        return self._config

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.row() == 0:
                return str(self._config.data_path)

    # noinspection PyTypeChecker
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid():
            return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            if index.row() == 0:
                self._config.data_path = value
                return True
        return False
