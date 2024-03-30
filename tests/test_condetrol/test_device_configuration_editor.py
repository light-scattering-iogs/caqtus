from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from caqtus.device import DeviceName
from caqtus.gui.condetrol.device_configuration_editors import (
    DeviceConfigurationsDialog,
    default_device_configuration_plugin,
)
from caqtus.gui.condetrol.device_configuration_editors.configurations_editor import (
    DeviceConfigurationsView,
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
    view = DeviceConfigurationsView(
        default_device_configuration_plugin.editor_factory, parent=None
    )
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


def test_edit_1(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
        DeviceName("Device 2"): MockDeviceConfiguration(remote_server="default"),
    }
    view = DeviceConfigurationsView(
        default_device_configuration_plugin.editor_factory, parent=None
    )
    view.set_device_configurations(device_configurations)
    qtbot.addWidget(view)

    first_index = view.model().index(0, 0)
    view.setCurrentIndex(first_index)
    editor = view.previewWidget()
    assert isinstance(editor, DefaultDeviceConfigurationEditor)
    assert editor.remote_server_line_edit.text() == "default"
    editor.remote_server_line_edit.setText("new")
    view.setCurrentIndex(view.model().index(1, 0))
    new_configs = view.get_device_configurations()
    assert new_configs[DeviceName("Device 1")].remote_server == "new"
    assert new_configs[DeviceName("Device 2")].remote_server == "default"


def test_name_edit(qtbot: QtBot):
    device_configurations = {
        DeviceName("Device 1"): MockDeviceConfiguration(remote_server="default"),
    }
    view = DeviceConfigurationsView(
        default_device_configuration_plugin.editor_factory, parent=None
    )
    view.set_device_configurations(device_configurations)
    qtbot.addWidget(view)

    # need to click before double click
    qtbot.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        view.visualRect(view.model().index(0, 0)).center(),
    )
    qtbot.mouseDClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        view.visualRect(view.model().index(0, 0)).center(),
    )
    qtbot.keyClicks(view.focusWidget(), "New Name")
    qtbot.keyClick(view.focusWidget(), Qt.Key_Return)
    qtbot.wait_until(lambda: view._model.stringList() == ["New Name"])
    assert (
        view.get_device_configurations()[DeviceName("New Name")]
        == device_configurations[DeviceName("Device 1")]
    )


def test_add_config(qtbot: QtBot):
    config = MockDeviceConfiguration(remote_server="default")
    view = DeviceConfigurationsView(
        default_device_configuration_plugin.editor_factory, parent=None
    )
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
    dialog = DeviceConfigurationsDialog(
        default_device_configuration_plugin,
        parent=None,
    )
    qtbot.addWidget(dialog)
