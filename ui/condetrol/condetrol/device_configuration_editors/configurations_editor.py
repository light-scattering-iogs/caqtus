from collections.abc import Mapping, Iterable
from typing import TypedDict, Optional

from PyQt6.QtGui import QValidator
from PyQt6.QtWidgets import QDialog, QPushButton

from core.device import DeviceConfigurationAttrs, DeviceName
from .add_device_dialog_ui import Ui_AddDeviceDialog
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
        self._add_button = QPushButton("Add...")

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        self.setupUi(self)
        self.tab_widget.clear()
        self.tab_widget.setCornerWidget(self._add_button)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.tab_widget.removeTab)
        self.tab_widget.setMovable(True)
        for device_name, device_configuration in self.device_configurations.items():
            device_configuration_editor = self.device_configuration_edit_info[
                type(device_configuration).__qualname__
            ]["editor_type"]()
            self.tab_widget.addTab(device_configuration_editor, device_name)
            device_configuration_editor.set_configuration(device_configuration)

    def setup_connections(self):
        # noinspection PyUnresolvedReferences
        self._add_button.clicked.connect(self.add_configuration)

    def add_configuration(self):
        validator = NewNameValidator(
            self.tab_widget.tabText(i) for i in range(self.tab_widget.count())
        )
        add_device_dialog = AddDeviceDialog(
            self.device_configuration_edit_info.keys(),
            validator,
        )
        result = add_device_dialog.exec()
        if result is not None:
            device_name, device_type = result
            device_configuration_editor = self.device_configuration_edit_info[
                device_type
            ]["editor_type"]()
            self.tab_widget.addTab(device_configuration_editor, device_name)

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


class AddDeviceDialog(QDialog, Ui_AddDeviceDialog):
    def __init__(
        self, device_types: Iterable[str], validator: QValidator, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.setup_ui(device_types)
        self.device_name_line_edit.setValidator(validator)

    def setup_ui(self, device_types: Iterable[str]):
        self.setupUi(self)
        for device_type in device_types:
            self.device_type_combo_box.addItem(device_type)

    def exec(self) -> Optional[tuple[DeviceName, str]]:
        result = super().exec()
        if result == QDialog.DialogCode.Accepted:
            if not self.device_name_line_edit.hasAcceptableInput():
                return None
            device_name = self.device_name_line_edit.text()
            device_type = self.device_type_combo_box.currentText()
            return device_name, device_type
        return None


class NewNameValidator(QValidator):
    def __init__(self, already_used_names: Iterable[str]):
        super().__init__()
        self.already_used_names = set(already_used_names)

    def validate(self, a0, a1):
        if a0 in self.already_used_names or a0 == "":
            return QValidator.State.Intermediate, a0, a1
        else:
            return QValidator.State.Acceptable, a0, a1
