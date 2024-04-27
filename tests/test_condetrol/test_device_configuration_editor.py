from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from caqtus.device import DeviceName
from caqtus.gui.condetrol.device_configuration_editors import (
    DeviceConfigurationsDialog,
)
from caqtus.gui.condetrol.device_configuration_editors.configurations_editor import (
    DeviceConfigurationsView,
    DeviceConfigurationsPlugin,
)
from caqtus.gui.condetrol.device_configuration_editors.device_configuration_editor import (
    FormDeviceConfigurationEditor,
)
from tests.test_condetrol.mock_device_configuration import MockDeviceConfiguration


def test_edit(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
        DeviceName("Device 2"): MockDeviceConfiguration(remote_server="default"),
    }
    widget = DeviceConfigurationsView(DeviceConfigurationsPlugin.default(), parent=None)
    widget.set_device_configurations(device_configurations)
    qtbot.addWidget(widget)
    widget.show()

    widget.edit(0)
    editor = widget.editor()
    assert isinstance(editor, FormDeviceConfigurationEditor)
    assert editor.remote_server_line_edit.text() == "default"
    editor.remote_server_line_edit.setText("new")
    new_configs = widget.get_device_configurations()
    assert new_configs[DeviceName("Device 1")].remote_server == "new"
    assert new_configs[DeviceName("Device 2")].remote_server == "default"


def test_edit_1(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
        DeviceName("Device 2"): MockDeviceConfiguration(remote_server="default"),
    }
    widget = DeviceConfigurationsView(DeviceConfigurationsPlugin.default(), parent=None)
    widget.set_device_configurations(device_configurations)
    qtbot.addWidget(widget)

    widget.edit(0)
    editor = widget.editor()
    assert isinstance(editor, FormDeviceConfigurationEditor)
    assert editor.remote_server_line_edit.text() == "default"
    editor.remote_server_line_edit.setText("new")
    widget._list_view.setCurrentIndex(widget._model.index(1, 0))
    new_configs = widget.get_device_configurations()
    assert new_configs[DeviceName("Device 1")].remote_server == "new"
    assert new_configs[DeviceName("Device 2")].remote_server == "default"


def test_add_config(qtbot: QtBot):
    config = MockDeviceConfiguration(remote_server="default")
    view = DeviceConfigurationsView(DeviceConfigurationsPlugin.default(), parent=None)
    qtbot.addWidget(view)
    view.add_configuration(DeviceName("Device 1"), config)
    assert view.get_device_configurations() == {DeviceName("Device 1"): config}
    view.add_configuration(DeviceName("Device 2"), config)
    assert view.get_device_configurations() == {
        DeviceName("Device 1"): config,
        DeviceName("Device 2"): config,
    }
    view.add_configuration(DeviceName("Device 1"), config)
    assert view.get_device_configurations() == {
        DeviceName("Device 1"): config,
        DeviceName("Device 2"): config,
    }


def test_dialog(qtbot: QtBot):
    plugin = DeviceConfigurationsPlugin.default()
    plugin.register_default_configuration(
        "Mock", lambda: MockDeviceConfiguration(remote_server=None)
    )
    dialog = DeviceConfigurationsDialog(
        device_configurations_plugin=plugin,
        parent=None,
    )
    dialog.set_device_configurations(
        {
            DeviceName("Device 1"): MockDeviceConfiguration(remote_server=None),
            DeviceName("Device 2"): MockDeviceConfiguration(remote_server=None),
        }
    )
    dialog.show()
    qtbot.addWidget(dialog)
