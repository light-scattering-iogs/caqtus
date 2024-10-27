import attrs

from caqtus.device import DeviceConfiguration
from caqtus.device.output_transform import EvaluableOutput
from caqtus.types.expression import Expression
from caqtus.gui.autogen import build_device_configuration_editor


@attrs.define
class DeviceWithOutputTransform(DeviceConfiguration):
    output: EvaluableOutput


def test_output_transform_editor(qtbot):
    device = DeviceWithOutputTransform(remote_server=None, output=Expression("1 + 1"))

    editor_type = build_device_configuration_editor(DeviceWithOutputTransform)
    editor = editor_type(device)
    editor.show()
    qtbot.addWidget(editor)
    qtbot.stop()
