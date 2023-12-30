from collections.abc import Mapping
from typing import TypedDict

from PyQt6.QtWidgets import QDialog

from core.device import DeviceConfigurationAttrs, DeviceName
from .configurations_editor_ui import Ui_ConfigurationsEditor
from .device_configuration_editor import DeviceConfigurationEditor


class DeviceConfigurationEditInfo[T: DeviceConfigurationAttrs](TypedDict):
    editor_type: type[DeviceConfigurationEditor[T]]


class ConfigurationsEditor(QDialog, Ui_ConfigurationsEditor):
    def __init__(
        self,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
        device_configuration_edit_info: Mapping[str, DeviceConfigurationEditInfo],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.device_configurations = device_configurations
        self.device_configuration_edit_info = device_configuration_edit_info

        self.setup_ui()

    def setup_ui(self):
        self.setupUi(self)
        self.tab_widget.clear()
        for device_name, device_configuration in self.device_configurations.items():
            device_configuration_editor = self.device_configuration_edit_info[
                type(device_configuration).__qualname__
            ]["editor_type"]()
            self.tab_widget.addTab(device_configuration_editor, device_name)
            device_configuration_editor.set_configuration(device_configuration)

    def exec(self):
        result = super().exec()
        if result == QDialog.DialogCode.Accepted:
            device_configurations = {}
            for i in range(self.tab_widget.count()):
                device_configuration_editor = self.tab_widget.widget(i)
                device_configuration = device_configuration_editor.get_configuration()
                device_configurations[self.tab_widget.tabText(i)] = device_configuration
            self.device_configurations = device_configurations
        return result
