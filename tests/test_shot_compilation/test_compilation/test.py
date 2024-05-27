from caqtus.shot_compilation import SequenceContext
from caqtus.utils.roi import RectangularROI
from .device_configurations import device_configurations
from .lanes import lanes
from caqtus_devices.orca_quest import orca_quest_extension


def test_camera():
    sequence_context = SequenceContext(device_configurations, lanes)
    orca_quest_compiler = orca_quest_extension.compiler_type(
        "Orca Quest", sequence_context
    )

    initialization_parameters = orca_quest_compiler.compile_initialization_parameters()
    expected = {
        "camera_number": 0,
        "external_trigger": True,
        "name": "Orca Quest",
        "roi": RectangularROI(
            original_image_size=(4096, 2304), x=1948, width=440, y=848, height=400
        ),
        "timeout": 1.0,
    }
    assert initialization_parameters == expected
