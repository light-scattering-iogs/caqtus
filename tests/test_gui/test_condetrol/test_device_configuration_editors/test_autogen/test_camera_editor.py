import attrs
from pytestqt.qtbot import QtBot

from caqtus.device.camera import CameraConfiguration
from caqtus.gui.autogen import build_device_configuration_editor
from caqtus.types.image import Width, Height
from caqtus.types.image.roi import RectangularROI


@attrs.define
class OrcaQuestCameraConfiguration(CameraConfiguration):
    """Contains the necessary information about an Orca Quest  Hamamatsu camera.

    Attributes:
        camera_number: The number by which to identify the camera.
    """

    camera_number: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)
    roi: RectangularROI = CameraConfiguration.roi


def test(qtbot: QtBot):

    editor_type = build_device_configuration_editor(OrcaQuestCameraConfiguration)

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
    qtbot.stop()
    assert editor.get_configuration() == config
