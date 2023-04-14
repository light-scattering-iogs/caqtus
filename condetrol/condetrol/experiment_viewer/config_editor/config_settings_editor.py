from abc import abstractmethod
from typing import Optional

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from device_config import DeviceConfiguration
from experiment.configuration import ExperimentConfig
from qabc import QABC
from yaml_clipboard_mixin import YAMLClipboardMixin


class ConfigSettingsEditor(QWidget, QABC):
    """An abstract interface defining how a widget should edit a group of settings.

    Every time a settings group is selected in the config editor, a widget is created to
    edit that group. When it is created, the widget is passed a copy of the experiment
    config, and it assumes it is the only one that can modify it. The widget should then
    update the UI to match the config and when the user changes the settings, it should
    update the config to match the UI. The widget should also provide a method to return
     a copy of the config currently shown in the UI.

    Attributes:
        _experiment_config: The experiment config to edit. The widget assumes it is the
            only one that can modify it.
        _tree_label: The label as shown in the tree widget.
    """

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the widget.

        Args:
            experiment_config: The experiment config to edit. The widget will take
                ownership of the object and assumes that it is the only one that can
                modify it.
            tree_label: The label to show in the tree widget.
            parent: The parent widget.
        """

        super().__init__(parent)
        self._experiment_config = experiment_config
        self._tree_label = tree_label

    @abstractmethod
    def get_experiment_config(self) -> ExperimentConfig:
        """Return a copy of the experiment config currently shown in the UI.

        This method is meant to be subclassed by the concrete implementation of the
        widget. The default implementation just returns a copy of the config passed to
        the constructor. An actual widget will rewrite some attributes of this config.

        A typical implementation would update the _experiment_config attribute from the
        UI and then return a copy of it::

        def get_experiment_config(self) -> ExperimentConfig:
            self._experiment_config = self.update_config(self._experiment_config)
            return super().get_experiment_config()
        """

        return self._experiment_config.copy(deep=True)


# noinspection PyAbstractClass
class DeviceConfigEditor(ConfigSettingsEditor, YAMLClipboardMixin, QABC):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)
        self.device_name = self.strip_device_prefix(tree_label)

    def convert_to_external_use(self):
        return self._experiment_config.get_device_config(self.device_name)

    def update_from_external_source(self, new_config: DeviceConfiguration):
        """Update the device config."""

        if new_config.device_name != self.device_name:
            raise ValueError(
                f"Cannot change device name from {self.device_name} to"
                f" {new_config.device_name}"
            )
        old_config = self._experiment_config.get_device_config(self.device_name)
        if not isinstance(new_config, type(old_config)):
            raise TypeError(f"Expected {type(old_config)} got {type(new_config)}")
        self._experiment_config.set_device_config(self.device_name, new_config)

    @staticmethod
    def strip_device_prefix(tree_label: str) -> str:
        """

        example: strip_device_prefix("Devices\\dev A") == "dev A"
        """

        prefix = tree_label[0:8]
        if prefix != "Devices\\":
            raise ValueError(
                f"Invalid prefix for device tree label: {tree_label} should start with"
                " 'Devices\\'"
            )
        return tree_label[8:]


class NotImplementedDeviceConfigEditor(DeviceConfigEditor):
    """A widget that shows a message that the device type is not implemented."""

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        device_config = self._experiment_config.get_device_config(self.device_name)
        device_type = device_config.get_device_type()
        layout = QHBoxLayout()
        layout.addWidget(
            QLabel(
                f"There is no widget implemented for a device of type <{device_type}>"
            )
        )
        self.setLayout(layout)

    def get_experiment_config(self) -> ExperimentConfig:
        return super().get_experiment_config()
