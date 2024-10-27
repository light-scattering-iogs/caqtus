import attrs
from pytestqt.qtbot import QtBot

from caqtus.device.camera import CameraConfiguration
from caqtus.gui.condetrol.device_configuration_editors._autogen import (
    get_editor_builder,
    build_device_configuration_editor,
)
from caqtus.types.image import Width, Height
from caqtus.types.image.roi import RectangularROI


@attrs.define
class OrcaQuestCameraConfiguration(CameraConfiguration):
    camera_number: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)


def test(qtbot: QtBot):
    editor_type = build_device_configuration_editor(
        OrcaQuestCameraConfiguration, get_editor_builder()
    )

    config = OrcaQuestCameraConfiguration(
        camera_number=0,
        remote_server=None,
        roi=RectangularROI(
            original_image_size=(Width(4096), Height(2304)),
            x=0,
            y=0,
            width=4096,
            height=2304,
        ),
    )

    editor = editor_type(config)

    qtbot.addWidget(editor)
    editor.show()
    assert editor.get_configuration() == config
