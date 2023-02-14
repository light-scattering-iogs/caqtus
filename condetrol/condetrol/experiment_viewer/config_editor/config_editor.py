import logging
from copy import deepcopy
from pathlib import Path
from typing import Optional

from PyQt6 import QtGui
from PyQt6.QtCore import (
    QSettings,
)
from PyQt6.QtWidgets import (
    QDialog,
    QTreeWidgetItem,
    QLayout,
)

from experiment.configuration import ExperimentConfig
from settings_model import YAMLSerializable
from .config_editor_ui import Ui_config_editor
from .config_settings_editor import (
    ConfigSettingsEditor,
    NotImplementedDeviceConfigEditor,
)
from .devices_editor import DevicesEditor
from .sequence_header_editor import SequenceHeaderEditor
from .siglent_sdg_6000x_config_editor import SiglentSDG6000XConfigEditor
from .spincore_config_editor import SpincoreConfigEditor
from .system_settings_editor import SystemSettingsEditor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ConfigEditor(QDialog, Ui_config_editor):
    """A widget to edit the experiment config

    This widget is made of a settings tree to select a category of settings and a
    specific widget for each category
    """

    def __init__(self, experiment_config: ExperimentConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")
        self.setupUi(self)
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        assert isinstance(experiment_config, ExperimentConfig)
        self.config = experiment_config

        self.system_item = QTreeWidgetItem(self.category_tree)
        self.system_item.setText(0, "System")

        self.constants_item = QTreeWidgetItem(self.category_tree)
        self.constants_item.setText(0, "Constants")

        self.devices_item = QTreeWidgetItem(self.category_tree)
        self.devices_item.setText(0, "Devices")

        self.category_tree.currentItemChanged.connect(self.change_displayed_widget)

        self.update_device_tree()

    def get_config(self) -> ExperimentConfig:
        assert isinstance(self.config, ExperimentConfig)
        return self.config

    def update_device_tree(self):
        while self.devices_item.childCount():
            child = self.devices_item.child(0)
            self.devices_item.removeChild(child)

        for device_name in self.config.get_device_names():
            item = QTreeWidgetItem(self.devices_item)
            item.setText(0, device_name)

    def create_editor_widget(
        self,
        tree_label: str,
    ) -> ConfigSettingsEditor:
        if tree_label == "System":
            return SystemSettingsEditor(deepcopy(self.config), tree_label)
        elif tree_label == "Constants":
            return SequenceHeaderEditor(deepcopy(self.config), tree_label)
        elif tree_label == "Devices":
            editor = DevicesEditor(deepcopy(self.config), tree_label)
            editor.device_added.connect(self.on_device_added)
            return editor
        elif tree_label.startswith("Devices\\"):
            return self.create_widget_for_device(tree_label[8:])
        raise RuntimeError(f"Tree label {tree_label} has no associated widget")

    def on_device_added(self):
        self.change_displayed_widget(self.devices_item, None)
        self.update_device_tree()

    def create_widget_for_device(self, device_name: str):
        type_to_widget = {
            "SiglentSDG6000XWaveformGenerator": SiglentSDG6000XConfigEditor,
            "SpincorePulseBlaster": SpincoreConfigEditor,
        }

        device_type = self.config.get_device_config(device_name).get_device_type()

        widget_type = type_to_widget.get(device_type, NotImplementedDeviceConfigEditor)
        return widget_type(deepcopy(self.config), f"Devices\\{device_name}")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if widget := self.get_current_widget():
            self.config = widget.get_experiment_config()
        self.save_window_geometry()
        super().closeEvent(a0)

    def save_window_geometry(self):
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)

    def change_displayed_widget(self, item: QTreeWidgetItem, _):
        """Save the config from the previously displayed widget then display the new widget instead"""

        label = item.text(0)

        if old_widget := self.get_current_widget():
            config = old_widget.get_experiment_config()
            if not isinstance(config, ExperimentConfig):
                raise TypeError(
                    f"Widget {label} did not return an <ExperimentConfig> object"
                )
            self.config = config
            old_widget.deleteLater()

        if item.parent() is self.devices_item:
            label = f"Devices\\{label}"
        new_widget = self.create_editor_widget(label)

        self.widget_layout.addWidget(new_widget)

    def get_current_widget(self) -> Optional[ConfigSettingsEditor]:
        if self.widget_layout.count():
            return self.widget_layout.itemAt(0).widget()
        else:
            return None


def clear_layout(layout: QLayout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


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
                (
                    f"Unable to load {config_path}. Loading a default configuration"
                    " instead."
                ),
                exc_info=True,
            )
            config = ExperimentConfig()
    else:
        config = ExperimentConfig()
    return config
