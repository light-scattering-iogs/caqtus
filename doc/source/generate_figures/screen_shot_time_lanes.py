from PySide6.QtCore import QRect, QPoint, QSize
from PySide6.QtWidgets import QAbstractScrollArea

from caqtus.extension import Experiment
from caqtus.gui.condetrol.timelanes_editor.time_lanes_editor import TimeLanesView
from caqtus.types.timelane import TimeLanes


def screenshot_time_lanes(time_lanes: TimeLanes, filename: str):
    exp = Experiment()
    exp.setup_default_extensions()
    view = TimeLanesView(exp._extension.condetrol_extension.lane_extension, {})
    view.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
    view.set_time_lanes(time_lanes)
    view.grab(QRect(QPoint(0, 0), QSize(-1, -1))).save(filename)
    view.deleteLater()
