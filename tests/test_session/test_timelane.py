from caqtus.types.timelane import DigitalTimeLane


def test_0():
    lane = DigitalTimeLane([True] * 5)
    assert lane == [True, True, True, True, True]

    lane[2] = False
    assert lane == [True, True, False, True, True], repr(lane)

    lane[-1] = False
    assert lane == [True, True, False, True, False], repr(lane)


def test_1():
    lane = DigitalTimeLane([True])

    lane[0] = False
    assert lane == [False], repr(lane)


def test_2():
    lane = DigitalTimeLane([True] * 5)

    lane.insert(2, False)

    assert lane == [True, True, False, True, True, True], repr(lane)

    lane.insert(0, False)
    assert lane == [False, True, True, False, True, True, True], repr(lane)


def test_3():
    lane = DigitalTimeLane.from_spanned_values([(True, 2), (False, 1), (True, 3)])

    lane[0] = False
    assert lane == [False, True, False, True, True, True], repr(lane)


def test_4():
    lane = DigitalTimeLane.from_spanned_values([(True, 1)])

    lane.insert(1, False)
    assert lane == [True, False], repr(lane)


def test_5():
    lane = DigitalTimeLane.from_spanned_values([(True, 5)])

    lane[0:2] = False
    assert lane == [False, False, True, True, True], repr(lane)

    lane = DigitalTimeLane.from_spanned_values([(True, 5)])

    lane[3:5] = False
    assert lane == [True, True, True, False, False], repr(lane)


def test_6():
    lane = DigitalTimeLane.from_spanned_values([(True, 5)])

    lane[1:3] = False
    assert lane == [True, False, False, True, True], repr(lane)


def test_7():
    lane = DigitalTimeLane.from_spanned_values([(True, 3), (False, 2)])

    lane[1:4] = False
    assert lane == [True, False, False, False, False], repr(lane)
