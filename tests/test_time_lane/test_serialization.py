import pickle

from caqtus.types.timelane import DigitalTimeLane
from caqtus.types.timelane.serializer import TimeLaneSerializer
from caqtus.extension.time_lane_extension._digital_time_lane_exension import (
    dump_digital_lane,
    load_digital_lane,
)


def test():
    s = TimeLaneSerializer()
    s.register_time_lane(
        DigitalTimeLane,
        dump_digital_lane,
        load_digital_lane,
        type_tag="digital",
    )
    lane = DigitalTimeLane([False, True, False])
    assert s.load(s.dump(lane)) == lane

    r = pickle.loads(pickle.dumps(s))
    assert r.load(r.dump(lane)) == lane
