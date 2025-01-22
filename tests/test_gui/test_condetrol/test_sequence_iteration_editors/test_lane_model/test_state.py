from hypothesis.stateful import (
    RuleBasedStateMachine,
    run_state_machine_as_test,
    rule,
    precondition,
)
from hypothesis.strategies import integers, data

from caqtus.gui.condetrol.timelanes_editor._time_lanes_model import TimeLanesModel


class TimeLaneModelMachine(RuleBasedStateMachine):
    def __init__(self, lane_extension):
        super().__init__()
        self.model = TimeLanesModel(lane_extension)

    @rule(data=data())
    def insert_column(self, data):
        previous_number_steps = self.model.columnCount()
        column = data.draw(integers(0, previous_number_steps))
        self.model.insertColumn(column)
        assert self.model.columnCount() == previous_number_steps + 1

    @precondition(lambda self: self.model.columnCount() > 0)
    @rule(data=data())
    def remove_column(self, data):
        previous_number_steps = self.model.columnCount()
        column = data.draw(integers(0, previous_number_steps - 1))
        self.model.removeColumn(column)
        assert self.model.columnCount() == previous_number_steps - 1

    @precondition(lambda self: self.model.undo_stack.count() > 0)
    @rule(data=data())
    def undo_redo(self, data):
        actions_count = self.model.undo_stack.count()
        # index is defined this way such that it shrinks toward large index.
        index = actions_count - data.draw(integers(1, actions_count))
        previous_time_lanes = self.model.get_timelanes()
        self.model.undo_stack.setIndex(index)
        self.model.undo_stack.setIndex(actions_count)
        current_time_lanes = self.model.get_timelanes()
        assert previous_time_lanes == current_time_lanes


def test_lane_model(lane_extension):
    run_state_machine_as_test(lambda: TimeLaneModelMachine(lane_extension))
