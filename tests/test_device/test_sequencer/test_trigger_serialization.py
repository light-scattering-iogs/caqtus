from caqtus.device.sequencer.trigger import (
    SoftwareTrigger,
    ExternalTriggerStart,
    TriggerEdge,
    Trigger,
    ExternalClock,
    ExternalClockOnChange,
)
from caqtus.device.sequencer import converter


def test_trigger_serialization():
    triggers = [
        SoftwareTrigger(),
        ExternalTriggerStart(edge=TriggerEdge.RISING),
        ExternalClock(edge=TriggerEdge.BOTH),
        ExternalClockOnChange(edge=TriggerEdge.FALLING),
    ]
    s = converter.unstructure(triggers, unstructure_as=list[Trigger])
    t = converter.structure(s, list[Trigger])
    assert triggers == t
