from pytestqt.qtbot import QtBot

from caqtus.device import DeviceName
from caqtus.device.configuration import DeviceServerName
from caqtus.gui.condetrol.device_configuration_editors._configurations_editor import (
    DeviceConfigurationsDialog,
)
from caqtus.gui.condetrol.device_configuration_editors._configurations_editor import (
    DeviceConfigurationsEditor,
)
from caqtus.gui.condetrol.device_configuration_editors._device_configuration_editor import (
    FormDeviceConfigurationEditor,
)
from caqtus.gui.condetrol.device_configuration_editors._extension import (
    CondetrolDeviceExtension,
)
from tests.test_condetrol.mock_device_configuration import MockDeviceConfiguration


def test_edit(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
        DeviceName("Device 2"): MockDeviceConfiguration(remote_server="default"),
    }
    widget = DeviceConfigurationsEditor(CondetrolDeviceExtension(), parent=None)
    widget.set_device_configurations(device_configurations)
    qtbot.addWidget(widget)
    widget.show()

    widget.edit(0)
    editor = widget.editor()
    assert isinstance(editor, FormDeviceConfigurationEditor)
    assert editor.read_remote_server() == DeviceServerName("default")
    editor.set_remote_server(DeviceServerName("new"))
    new_configs = widget.get_device_configurations()
    assert new_configs[DeviceName("Device 1")].remote_server == "new"
    assert new_configs[DeviceName("Device 2")].remote_server == "default"


def test_edit_1(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
        DeviceName("Device 2"): MockDeviceConfiguration(remote_server="default"),
    }
    widget = DeviceConfigurationsEditor(CondetrolDeviceExtension(), parent=None)
    widget.set_device_configurations(device_configurations)
    widget.show()
    qtbot.addWidget(widget)

    widget.edit(0)
    editor = widget.editor()
    assert isinstance(editor, FormDeviceConfigurationEditor)
    assert editor.read_remote_server() == "default"
    editor.set_remote_server("new")
    widget._list_view.setCurrentIndex(widget._model.index(1, 0))
    new_configs = widget.get_device_configurations()
    assert new_configs[DeviceName("Device 1")].remote_server == "new"
    assert new_configs[DeviceName("Device 2")].remote_server == "default"


def test_add_config(qtbot: QtBot):
    config = MockDeviceConfiguration(remote_server="default")
    view = DeviceConfigurationsEditor(CondetrolDeviceExtension(), parent=None)
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
    extension = CondetrolDeviceExtension()
    extension.register_configuration_factory(
        "Mock", lambda: MockDeviceConfiguration(remote_server=None)
    )
    dialog = DeviceConfigurationsDialog(
        extension=extension,
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
