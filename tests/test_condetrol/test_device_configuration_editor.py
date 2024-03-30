from pytestqt.qtbot import QtBot

from caqtus.device import DeviceName
from caqtus.gui.condetrol.device_configuration_editors.configurations_editor import (
    DeviceConfigurationsView,
    default_device_editor_factory,
)
from caqtus.gui.condetrol.device_configuration_editors.device_configuration_editor import (
    DefaultDeviceConfigurationEditor,
)
from tests.test_condetrol.mock_device_configuration import MockDeviceConfiguration


def test_edit(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
        DeviceName("Device 2"): MockDeviceConfiguration(remote_server="default"),
    }
    view = DeviceConfigurationsView(default_device_editor_factory, parent=None)
    view.set_device_configurations(device_configurations)
    qtbot.addWidget(view)

    first_index = view.model().index(0, 0)
    view.setCurrentIndex(first_index)
    editor = view.previewWidget()
    assert isinstance(editor, DefaultDeviceConfigurationEditor)
    assert editor.remote_server_line_edit.text() == "default"
    editor.remote_server_line_edit.setText("new")
    new_configs = view.get_device_configurations()
    assert new_configs[DeviceName("Device 1")].remote_server == "new"
    assert new_configs[DeviceName("Device 2")].remote_server == "default"
