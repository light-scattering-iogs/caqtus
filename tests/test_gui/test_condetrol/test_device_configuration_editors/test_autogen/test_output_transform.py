import attrs

from caqtus.device import DeviceConfiguration
from caqtus.device.output_transform import EvaluableOutput
from caqtus.gui.autogen import generate_device_configuration_editor
from caqtus.types.expression import Expression


@attrs.define
class DeviceWithOutputTransform(DeviceConfiguration):
    output: EvaluableOutput


def test_output_transform_editor(qtbot):
    device = DeviceWithOutputTransform(remote_server=None, output=Expression("1 + 1"))

    editor_type = generate_device_configuration_editor(DeviceWithOutputTransform)
    editor = editor_type(device)
    editor.show()
    qtbot.addWidget(editor)
