import copy
from abc import abstractmethod
from typing import Optional, Type

from PyQt6.QtWidgets import QWidget, QHBoxLayout

from device.configuration import DeviceConfiguration
from device.configuration_editor import (
    DeviceConfigEditor,
    NotImplementedDeviceDeviceConfigEditor,
)
from device.name import DeviceName
from experiment.configuration import ExperimentConfig
from qabc import QABC
from spincore_sequencer.configuration_editor import (
    SpincorePulseBlasterDeviceConfigEditor,
)
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
            experiment_config: The experiment config to edit.
            tree_label: The label to show in the tree widget.
            parent: The parent widget.
        """

        super().__init__(parent)
        self._experiment_config = copy.deepcopy(experiment_config)
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


class WrapDeviceConfigEditor(ConfigSettingsEditor, YAMLClipboardMixin, QABC):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)
        self._device_name = DeviceName(self._tree_label[8:])
        self._device_type = self._experiment_config.get_device_runtime_type(
            self._device_name
        )
        self._device_config_editor = self.create_widget_for_device(self._device_name)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._device_config_editor)

    def create_widget_for_device(self, device_name: DeviceName) -> DeviceConfigEditor:
        """Create a widget to edit the config of a device.

        This function asks the experiment config what is the device type associated
        with the device name and create the appropriate widget to edit this kind of
        device. If there is no widget registered for this device type,
        a NotImplementedDeviceConfigEditor is returned that only displays the device
        type.
        """

        type_to_widget: dict[str, Type[DeviceConfigEditor]] = {
            # "SpincorePulseBlaster": SpincorePulseBlasterDeviceConfigEditor,
            # "NI6738AnalogCard": NI6738ConfigEditor,
            # "ElliptecELL14RotationStage": ElliptecELL14RotationStageConfigEditor,
            # "OrcaQuestCamera": OrcaQuestConfigEditor,
        }

        widget_type = type_to_widget.get(
            self._device_type, NotImplementedDeviceDeviceConfigEditor
        )
        return widget_type(
            self._experiment_config.get_device_config(device_name),
            set(self._experiment_config.device_servers.keys()),
        )

    def get_experiment_config(self) -> ExperimentConfig:
        experiment_config = super().get_experiment_config()
        experiment_config.set_device_config(
            self._device_name, self._device_config_editor.get_device_config()
        )
        return experiment_config

    def convert_to_external_use(self) -> DeviceConfiguration:
        return self._device_config_editor.get_device_config()

    def update_from_external_source(self, external_source: DeviceConfiguration):
        if not isinstance(external_source, DeviceConfiguration):
            raise TypeError(
                f"Expected a DeviceConfiguration, got {type(external_source)}")
        self._device_config_editor.update_ui(external_source)
