from abc import ABC, abstractmethod
from enum import Enum

from attr import define

import serialization
from settings_model.yaml_serializable import yaml, YAMLSerializable


class TriggerEdge(Enum):
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"


@define
class Trigger(ABC):
    def is_software_trigger(self) -> bool:
        return isinstance(self, SoftwareTrigger)

    def is_external_trigger_start(self) -> bool:
        return isinstance(self, ExternalTriggerStart)

    def is_external_clock(self) -> bool:
        return isinstance(self, ExternalClock)

    @property
    @abstractmethod
    def priority(self) -> int:
        """The priority of the trigger.

        Triggers with higher priority should be started before triggers with lower priority. This is used to determine
        the order in which the devices are started if a device should be triggered by another.
        """
        raise NotImplementedError


@define
class SoftwareTrigger(Trigger):
    @property
    def priority(self) -> int:
        return 0


@define
class ExternalTriggerStart(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


@define
class ExternalClock(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


@define
class ExternalClockOnChange(Trigger):
    edge: TriggerEdge = TriggerEdge.RISING

    @property
    def priority(self) -> int:
        return 1


serialization.include_subclasses(Trigger, union_strategy=serialization.include_type(tag_name="trigger_type"))


def trigger_representer(dumper: yaml.Dumper, value: Trigger):
    return dumper.represent_mapping(
        f"!Trigger",
        serialization.unstructure(value),
    )


YAMLSerializable.get_dumper().add_representer(Trigger, trigger_representer)
YAMLSerializable.get_dumper().add_representer(SoftwareTrigger, trigger_representer)
YAMLSerializable.get_dumper().add_representer(ExternalTriggerStart, trigger_representer)
YAMLSerializable.get_dumper().add_representer(ExternalClock, trigger_representer)
YAMLSerializable.get_dumper().add_representer(ExternalClockOnChange, trigger_representer)


def trigger_constructor(loader: yaml.Loader, node: yaml.SequenceNode):
    return serialization.structure(loader.construct_mapping(node), Trigger)


YAMLSerializable.get_loader().add_constructor(f"!Trigger", trigger_constructor)
