from core.session.shot import DigitalTimeLane


def test_0():
    lane = DigitalTimeLane([(True, 5)])
    assert lane == [True, True, True, True, True]

    lane[2] = False
    assert lane == [True, True, False, True, True], repr(lane)

    lane[-1] = False
    assert lane == [True, True, False, True, False], repr(lane)


def test_1():
    lane = DigitalTimeLane([(True, 1)])

    lane[0] = False
    assert lane == [False], repr(lane)
