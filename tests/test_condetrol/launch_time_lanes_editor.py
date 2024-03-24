from PySide6.QtWidgets import QApplication


from caqtus.gui.condetrol.timelanes_editor import (
    TimeLanesEditor,
    default_lane_model_factory,
    default_lane_delegate_factory,
)

app = QApplication([])

editor = TimeLanesEditor(
    lane_model_factory=default_lane_model_factory,
    lane_delegate_factory=default_lane_delegate_factory,
    device_configurations={},
)
editor.show()
app.exec()
