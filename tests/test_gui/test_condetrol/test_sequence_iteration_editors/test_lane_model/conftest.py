import pytest

from caqtus.extension.time_lane_extension import digital_time_lane_extension
from caqtus.gui.condetrol.timelanes_editor.extension import (
    CondetrolLaneExtension,
    CondetrolLaneExtensionProtocol,
)
from caqtus.types.timelane import DigitalTimeLane


@pytest.fixture(scope="module")
def lane_extension() -> CondetrolLaneExtensionProtocol:
    ext = CondetrolLaneExtension()
    ext.register_lane_model_factory(
        DigitalTimeLane, digital_time_lane_extension.lane_model_factory
    )
    return ext
