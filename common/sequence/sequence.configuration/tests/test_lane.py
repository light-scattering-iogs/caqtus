from typing import Type

from hypothesis.stateful import Bundle, RuleBasedStateMachine, initialize, rule
from hypothesis.strategies import (
    composite,
    DrawFn,
    integers,
    booleans,
    text,
    sampled_from,
    data,
)

from sequence.shot import TLane, DigitalLane, Lane

lane_type_strategy = sampled_from([DigitalLane])


@composite
def lane_value_strategy(draw: DrawFn, lane_type: Type[TLane]):
    if lane_type == DigitalLane:
        return draw(booleans())


@composite
def lane_strategy(draw: DrawFn, type_strategy=lane_type_strategy):
    lane_type = draw(type_strategy)
    size = draw(integers(min_value=0, max_value=10))
    spans = []
    values = []

    while (spanned := sum(spans)) < size:
        span = draw(integers(min_value=1, max_value=size - spanned))
        spans.append(span)
        value = draw(lane_value_strategy(lane_type))
        values += [value] * span
        spans += [0] * (span - 1)
    return lane_type(
        name=draw(text(max_size=20)), values=tuple(values), spans=tuple(spans)
    )


@composite
def lane_and_index_strategy(draw: DrawFn, lane_type: Type[TLane]):
    lane = draw(lane_strategy(lane_type))
    index = draw(integers(min_value=0, max_value=len(lane)))
    return lane, index


class LaneOperations(RuleBasedStateMachine):
    lanes = Bundle("lanes")

    @initialize(target=lanes, lane=lane_strategy())
    def create_lane(self, lane):
        return lane

    @rule(lane=lanes, data=data())
    def insert(self, lane: Lane, data):
        index = data.draw(integers(min_value=0, max_value=len(lane)), label="index")
        value = data.draw(lane_value_strategy(DigitalLane), label="value")
        previous_length = len(lane)
        if index < len(lane) and lane.spans[index] == 0:
            expected_value = lane[index]
        else:
            expected_value = value
        lane.insert(index, value)
        assert lane[index] == expected_value
        assert len(lane) == previous_length + 1

    @rule(lane=lanes, data=data())
    def remove(self, lane: Lane, data):
        if len(lane) > 0:
            index = data.draw(
                integers(min_value=0, max_value=len(lane) - 1), label="index"
            )
            previous_length = len(lane)
            lane.remove(index)
            assert len(lane) == previous_length - 1

    @rule(lane=lanes, data=data())
    def merge(self, lane: Lane, data):
        if len(lane) > 0:
            values = [lane[index] for index in range(len(lane))]
            start = data.draw(
                integers(min_value=0, max_value=len(lane) - 1), label="start"
            )
            stop = data.draw(
                integers(min_value=start + 1, max_value=len(lane)), label="stop"
            )
            value = lane[start]
            effective_start, _ = lane.span(start)
            _, effective_stop = lane.span(stop - 1)
            for index in range(effective_start, effective_stop):
                values[index] = value
            lane.merge(start, stop)
            assert all(lane[index] == values[index] for index in range(len(lane)))

    @rule(lane=lanes, data=data())
    def break_(self, lane: Lane, data):
        if len(lane) > 0:
            values = [lane[index] for index in range(len(lane))]
            start = data.draw(
                integers(min_value=0, max_value=len(lane) - 1), label="start"
            )
            stop = data.draw(
                integers(min_value=start + 1, max_value=len(lane)), label="stop"
            )
            effective_start, _ = lane.span(start)
            _, effective_stop = lane.span(stop - 1)
            for index in range(effective_start, effective_stop):
                values[index] = lane[index]
            lane.break_(start, stop)
            assert all(lane[index] == values[index] for index in range(len(lane)))


TestLaneOperations = LaneOperations.TestCase
