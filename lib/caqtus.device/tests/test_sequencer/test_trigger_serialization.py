from caqtus.device.sequencer.configuration.trigger import (
    SoftwareTrigger,
    ExternalTriggerStart,
    TriggerEdge,
    Trigger,
    ExternalClock,
    ExternalClockOnChange,
)
from caqtus.utils import serialization


def test_trigger_serialization():
    triggers = [
        SoftwareTrigger(),
        ExternalTriggerStart(edge=TriggerEdge.RISING),
        ExternalClock(edge=TriggerEdge.BOTH),
        ExternalClockOnChange(edge=TriggerEdge.FALLING),
    ]
    s = serialization.unstructure(triggers, unstructure_as=list[Trigger])
    t = serialization.structure(s, list[Trigger])
    assert triggers == t
