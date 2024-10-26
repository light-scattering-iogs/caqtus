from pytestqt.qtbot import QtBot

from caqtus.device import DeviceConfiguration
from caqtus.gui.condetrol.device_configuration_editors._autogen import (
    EditorBuilder,
    build_device_configuration_editor,
)


def test_simplest_class(qtbot: QtBot):
    class DeviceConfigA(DeviceConfiguration):
        pass

    value = DeviceConfigA(remote_server=None)

    builder = EditorBuilder()
    device_config_editor_type = build_device_configuration_editor(
        DeviceConfigA, builder
    )

    editor = device_config_editor_type(value)
    qtbot.add_widget(editor)
    editor.show()
