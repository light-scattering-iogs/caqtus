import decimal

from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor import (
    TimeStepEditor,
)


def test_set_value(qtbot):
    time_step_widget = TimeStepEditor(
        decimal.Decimal(1),
        2500,
        100000,
    )

    time_step_widget.set_time_step(decimal.Decimal(3000))
    time_step_widget.show()
    qtbot.addWidget(time_step_widget)

    assert time_step_widget.read_time_step() == decimal.Decimal(3000)
