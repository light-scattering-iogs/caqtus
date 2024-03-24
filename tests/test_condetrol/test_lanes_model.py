import pytest

from caqtus.gui.condetrol.timelanes_editor import TimeLanesModel, \
    default_lane_model_factory
from caqtus.session.shot import DigitalTimeLane


def test_0():
    model = TimeLanesModel(default_lane_model_factory)

    lane = DigitalTimeLane([True, False])
    with pytest.raises(ValueError):
        model.insert_timelane(0, "lane", lane)


def test_1():
    model = TimeLanesModel(default_lane_model_factory)

    model.insertColumn(0)
    model.insertColumn(0)

    lane = DigitalTimeLane([True, False])
    model.insert_timelane(0, "lane", lane)

    assert model.get_timelanes().lanes["lane"] == lane
