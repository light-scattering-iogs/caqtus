import pytest

from caqtus.device.sequencer.trigger import (
    ExternalTriggerStart,
    SoftwareTrigger,
    ExternalClock,
)
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor import (
    TriggerSelector,
)


def test_set_value(qtbot):
    widget = TriggerSelector({"Software", "External start"})

    widget.set_trigger(SoftwareTrigger())
    widget.show()
    qtbot.addWidget(widget)

    assert widget.currentText() == "Software"
    assert widget.get_trigger() == SoftwareTrigger()

    widget.set_trigger(ExternalTriggerStart())

    assert widget.currentText() == "External start"
    assert widget.get_trigger() == ExternalTriggerStart()

    with pytest.raises(ValueError):
        widget.set_trigger(ExternalClock())
