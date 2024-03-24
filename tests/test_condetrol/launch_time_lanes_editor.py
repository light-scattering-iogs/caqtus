import logging

from PySide6.QtWidgets import QApplication

from caqtus.gui.condetrol.timelanes_editor import (
    TimeLanesEditor,
    default_lane_model_factory,
    default_lane_delegate_factory,
)
from caqtus.session.shot import TimeLanes, DigitalTimeLane
from caqtus.types.expression import Expression

logging.basicConfig(level=logging.DEBUG)

app = QApplication([])
app.setApplicationName("TimeLanesEditor")


def create_digital_lane(number_steps: int) -> DigitalTimeLane:
    return DigitalTimeLane([False] * number_steps)


editor = TimeLanesEditor(
    lane_factories={"Digital": create_digital_lane},
    lane_model_factory=default_lane_model_factory,
    lane_delegate_factory=default_lane_delegate_factory,
    device_configurations={},
)

lanes = TimeLanes(
    step_names=["A", "B", "C"],
    step_durations=[Expression("1s"), Expression("2s"), Expression("3s")],
    lanes={"Test1": DigitalTimeLane([True, False, True])},
)
editor.set_time_lanes(lanes)
# editor.set_read_only(True)
editor.show()
app.exec()
