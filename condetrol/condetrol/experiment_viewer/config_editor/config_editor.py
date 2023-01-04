import logging
from copy import deepcopy
from pathlib import Path
from typing import Type, Optional

from PyQt5 import QtGui
from PyQt5.QtCore import (
    QSettings,
)
from PyQt5.QtWidgets import (
    QDialog,
    QTreeWidgetItem,
    QLayout,
)

from experiment_config import ExperimentConfig, get_config_path
from settings_model import YAMLSerializable
from .config_editor_ui import Ui_config_editor
from .config_settings_editor import ConfigSettingsEditor
from .sequence_header_editor import SequenceHeaderEditor
from .system_settings_editor import SystemSettingsEditor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ConfigEditor(QDialog, Ui_config_editor):
    """A widget to edit the experiment config file

    This widget is made of a settings tree to select a category of settings and a specific widget for each category
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")
        self.setupUi(self)
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        with open(get_config_path(), "r") as file:
            self.config = ExperimentConfig.from_yaml(file.read())

        self.settings_tree: dict[str, Type[ConfigSettingsEditor]] = dict()

        # To add a new category of settings, add a new entry in the dictionary below
        # The key is the name of the category and the value is the class that is
        # instantiated to create the editor widget.
        self.settings_tree["System"] = SystemSettingsEditor
        self.settings_tree["Constants"] = SequenceHeaderEditor

        for tree_label, widget_class in self.settings_tree.items():
            item = QTreeWidgetItem(self.category_tree)
            item.setText(0, tree_label)

        self.category_tree.currentItemChanged.connect(self.change_displayed_widget)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.save_experiment_config()
        self.save_window_geometry()
        super().closeEvent(a0)

    def save_experiment_config(self):
        if widget := self.get_current_widget():
            self.config = widget.get_experiment_config()
        with open(get_config_path(), "w") as file:
            file.write(self.config.to_yaml())

    def save_window_geometry(self):
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)

    def change_displayed_widget(self, item: QTreeWidgetItem, _):
        """Save the config from the previously displayed widget then display the new widget instead"""

        label = item.text(0)
        if widget := self.get_current_widget():
            self.config = widget.get_experiment_config()
        clear_layout(self.widget_layout)
        widget = self.settings_tree[label](deepcopy(self.config), label)
        self.widget_layout.addWidget(widget)

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
