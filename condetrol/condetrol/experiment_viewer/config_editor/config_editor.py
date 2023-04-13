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
from .config_editor_ui import Ui_ConfigEditor
from .config_settings_editor import (
    ConfigSettingsEditor,
    NotImplementedDeviceConfigEditor,
)
from .devices_editor import DevicesEditor
from .ni6738_config_editor import NI6738ConfigEditor
from .optimizer_config_editor import OptimizerConfigEditor
from .sequence_header_editor import SequenceHeaderEditor
from .siglent_sdg_6000x_config_editor import SiglentSDG6000XConfigEditor
from .spincore_config_editor import SpincoreConfigEditor
from .system_settings_editor import SystemSettingsEditor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ConfigEditor(QDialog, Ui_ConfigEditor):
    """A widget to edit the experiment config

    This widget is made of a settings tree to select a category of settings and a
    specific widget for each category.

    Args:
        experiment_config: The experiment config to edit. This object will be copied and
            the copy will be edited. The original object that was passed will not be
            modified.
    """

    def __init__(self, experiment_config: ExperimentConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._ui_settings = QSettings("Caqtus", "ExperimentControl")
        self._setup_ui(self._ui_settings)

        if not isinstance(experiment_config, ExperimentConfig):
            raise TypeError(
                f"Expected <ExperimentConfig> got {type(experiment_config)}"
            )
        self._config = deepcopy(experiment_config)
        self.update_device_tree()

    def _setup_ui(self, ui_settings: QSettings):
        """Set up the UI of the widget and restore the window geometry"""

        self.setupUi(self)
        self.restoreGeometry(
            ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        # Each of the item below represents a category of settings in the tree
        self._system_item = QTreeWidgetItem(self._category_tree)
        self._system_item.setText(0, "System")
        self._system_item.setToolTip(
            0, "Settings applied system-wide to the experiment."
        )
        self._constants_item = QTreeWidgetItem(self._category_tree)
        self._constants_item.setText(0, "Constants")
        self._constants_item.setToolTip(
            0,
            (
                "Declare constants that will be evaluated before running a sequence.\n"
                "Note that these constants will be declared after the devices are "
                "initialized."
            ),
        )
        self._optimization_item = QTreeWidgetItem(self._category_tree)
        self._optimization_item.setText(0, "Optimization")
        self._optimization_item.setToolTip(
            0, "Contain settings for running an optimization loop."
        )
        self._devices_item = QTreeWidgetItem(self._category_tree)
        self._devices_item.setText(0, "Devices")
        self._devices_item.setToolTip(0, "Settings for each device.")

        self._category_tree.currentItemChanged.connect(self.change_displayed_widget)

    def get_config(self) -> ExperimentConfig:
        """Return a copy of the current config shown in the widget"""

        return deepcopy(self._config)

    def update_device_tree(self):
        while self._devices_item.childCount():
            child = self._devices_item.child(0)
            self._devices_item.removeChild(child)

        for device_name in self._config.get_device_names():
            item = QTreeWidgetItem(self._devices_item)
            item.setText(0, device_name)

    def create_editor_widget(
        self,
        tree_label: str,
    ) -> ConfigSettingsEditor:
        if tree_label == "System":
            return SystemSettingsEditor(deepcopy(self._config), tree_label)
        elif tree_label == "Constants":
            return SequenceHeaderEditor(deepcopy(self._config), tree_label)
        elif tree_label == "Optimization":
            return OptimizerConfigEditor(deepcopy(self._config), tree_label)
        elif tree_label == "Devices":
            editor = DevicesEditor(deepcopy(self._config), tree_label)
            editor.device_added.connect(self.on_device_added)
            return editor
        elif tree_label.startswith("Devices\\"):
            return self.create_widget_for_device(tree_label[8:])
        raise RuntimeError(f"Tree label {tree_label} has no associated widget")

    def on_device_added(self):
        self.change_displayed_widget(self._devices_item, None)
        self.update_device_tree()

    def create_widget_for_device(self, device_name: str):
        type_to_widget = {
            "SiglentSDG6000XWaveformGenerator": SiglentSDG6000XConfigEditor,
            "SpincorePulseBlaster": SpincoreConfigEditor,
            "NI6738AnalogCard": NI6738ConfigEditor,
        }

        device_type = self._config.get_device_config(device_name).get_device_type()

        widget_type = type_to_widget.get(device_type, NotImplementedDeviceConfigEditor)
        return widget_type(deepcopy(self._config), f"Devices\\{device_name}")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if widget := self.get_current_widget():
            self._config = widget.get_experiment_config()
        self.save_window_geometry(self._ui_settings)
        super().closeEvent(a0)

    def save_window_geometry(self, ui_settings: QSettings):
        """Save the window geometry to be restored on next launch"""

        geometry = self.saveGeometry()
        ui_settings.setValue(f"{__name__}/geometry", geometry)

    def change_displayed_widget(self, item: QTreeWidgetItem, _):
        """Save the config from the previously displayed widget then display the new widget instead"""

        label = item.text(0)

        if old_widget := self.get_current_widget():
            config = old_widget.get_experiment_config()
            if not isinstance(config, ExperimentConfig):
                raise TypeError(
                    f"Widget {label} did not return an <ExperimentConfig> object"
                )
            self._config = config
            old_widget.deleteLater()

        if item.parent() is self._devices_item:
            label = f"Devices\\{label}"
        new_widget = self.create_editor_widget(label)

        self._widget_layout.addWidget(new_widget)

    def get_current_widget(self) -> Optional[ConfigSettingsEditor]:
        if self._widget_layout.count():
            return self._widget_layout.itemAt(0).widget()
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
