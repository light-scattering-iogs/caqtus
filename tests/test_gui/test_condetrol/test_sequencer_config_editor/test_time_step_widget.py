from caqtus.device.sequencer.timing import to_time_step
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor import (  # noqa: E501
    TimeStepEditor,
)


def test_set_value(qtbot):
    time_step_widget = TimeStepEditor(
        to_time_step(1),
        2500,
        100000,
    )

    time_step_widget.set_time_step(to_time_step(3000))
    time_step_widget.show()
    qtbot.addWidget(time_step_widget)

    assert time_step_widget.read_time_step() == to_time_step(3000)
