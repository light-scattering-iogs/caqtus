import pytest

from caqtus.extension.time_lane_extension import digital_time_lane_extension
from caqtus.gui.condetrol.timelanes_editor._time_lanes_model import TimeLanesModel
from caqtus.gui.condetrol.timelanes_editor.extension import CondetrolLaneExtension
from caqtus.types.timelane import DigitalTimeLane


def test_0():
    model = TimeLanesModel(CondetrolLaneExtension())

    lane = DigitalTimeLane([True, False])
    with pytest.raises(ValueError):
        model.insert_time_lane("lane", lane, 0)


def test_1():
    lane_extension = CondetrolLaneExtension()
    lane_extension.register_lane_model_factory(
        DigitalTimeLane, digital_time_lane_extension.lane_model_factory
    )
    model = TimeLanesModel(lane_extension)

    model.insertColumn(0)
    model.insertColumn(0)

    lane = DigitalTimeLane([True, False])
    model.insert_time_lane("lane", lane, 0)

    assert model.get_timelanes().lanes["lane"] == lane
