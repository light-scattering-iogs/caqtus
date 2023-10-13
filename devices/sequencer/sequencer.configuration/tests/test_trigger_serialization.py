import serialization
from sequencer.configuration.trigger import (
    SoftwareTrigger,
    ExternalTriggerStart,
    TriggerEdge,
    Trigger,
    ExternalClock,
)
from settings_model import YAMLSerializable


def test_trigger_serialization():
    triggers = [
        SoftwareTrigger(),
        ExternalTriggerStart(edge=TriggerEdge.RISING),
        ExternalClock(edge=TriggerEdge.BOTH),
    ]
    for t in triggers:
        assert t == serialization.structure(serialization.unstructure(t), Trigger)

    for t in triggers:
        assert t == YAMLSerializable.load(YAMLSerializable.dump(t))
