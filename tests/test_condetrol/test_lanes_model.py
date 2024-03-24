from caqtus.gui.condetrol.timelanes_editor import TimeLanesModel, default_lane_model_factory
from caqtus.session.shot import DigitalTimeLane


def test_0():
    model = TimeLanesModel(default_lane_model_factory)

    lane = DigitalTimeLane([])
    model.insert_timelane(0, "lane", lane)

    assert model.get_timelanes().lanes["lane"] == lane
