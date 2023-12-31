from core.device.sequencer.configuration.trigger import (
    SoftwareTrigger,
    ExternalTriggerStart,
    TriggerEdge,
    Trigger,
    ExternalClock,
)
from util import serialization


def test_trigger_serialization():
    triggers = [
        SoftwareTrigger(),
        ExternalTriggerStart(edge=TriggerEdge.RISING),
        ExternalClock(edge=TriggerEdge.BOTH),
    ]
    for t in triggers:
        assert t == serialization.structure(serialization.unstructure(t), Trigger)
