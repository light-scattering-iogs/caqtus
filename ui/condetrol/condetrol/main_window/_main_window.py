import copy
from collections.abc import Mapping

from PyQt6.QtWidgets import QMainWindow

from core.device import DeviceName, DeviceConfigurationAttrs
from core.session import ExperimentSessionMaker
from ._main_window_ui import Ui_CondetrolMainWindow
from ..device_configuration_editor import (
    DeviceConfigurationEditInfo,
    ConfigurationsEditor,
)


class CondetrolMainWindow(QMainWindow, Ui_CondetrolMainWindow):
    def __init__(
        self,
        session_maker: ExperimentSessionMaker,
        device_configuration_editors: Mapping[str, DeviceConfigurationEditInfo],
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.session_maker = session_maker
        self.device_configuration_edit_infos = device_configuration_editors
        self.setup_connections()

    def setup_connections(self):
        self.action_edit_device_configurations.triggered.connect(
            self.open_device_configurations_editor
        )

    def open_device_configurations_editor(self):
        with self.session_maker() as session:
            previous_device_configurations = dict(session.device_configurations)
        configurations_editor = ConfigurationsEditor(
            copy.deepcopy(previous_device_configurations),
            self.device_configuration_edit_infos,
        )
        configurations_editor.exec()
        self.update_device_configurations(
            previous_device_configurations, configurations_editor.device_configurations
        )

    def update_device_configurations(
        self,
        previous_device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
        new_device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ):
        to_remove = set(previous_device_configurations) - set(new_device_configurations)
        to_add = set(new_device_configurations) - set(previous_device_configurations)
        in_both = set(previous_device_configurations) & set(new_device_configurations)
        to_update = {
            device_name
            for device_name in in_both
            if new_device_configurations[device_name]
            != previous_device_configurations[device_name]
        }
        with self.session_maker() as session:
            for device_name in to_remove:
                del session.device_configurations[device_name]
            for device_name in to_add | to_update:
                session.device_configurations[device_name] = new_device_configurations[
                    device_name
                ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
