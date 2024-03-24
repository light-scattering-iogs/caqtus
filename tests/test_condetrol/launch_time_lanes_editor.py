import logging

from PySide6.QtWidgets import QApplication

from caqtus.gui.condetrol.timelanes_editor import (
    TimeLanesEditor,
    default_time_lanes_plugin,
)
from caqtus.session.shot import TimeLanes, DigitalTimeLane
from caqtus.types.expression import Expression

logging.basicConfig(level=logging.DEBUG)

app = QApplication([])
app.setApplicationName("TimeLanesEditor")


editor = TimeLanesEditor(
    time_lane_customization=default_time_lanes_plugin,
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
