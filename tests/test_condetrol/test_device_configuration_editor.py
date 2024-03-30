from pytestqt.qtbot import QtBot

from caqtus.device import DeviceName
from caqtus.gui.condetrol.device_configuration_editors.configurations_editor import (
    DeviceConfigurationsView,
    default_device_editor_factory,
)
from tests.test_condetrol.mock_device_configuration import MockDeviceConfiguration


def test(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
    }
    editor = DeviceConfigurationsView(default_device_editor_factory, parent=None)
    editor.set_device_configurations(device_configurations)
    qtbot.addWidget(editor)
    editor.show()
    qtbot.stop()
