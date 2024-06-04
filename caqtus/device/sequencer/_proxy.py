from typing import TypeVar

from caqtus.device.remote import DeviceProxy
from .instructions import SequencerInstruction
from .runtime import Sequencer
from .trigger import Trigger

SequencerType = TypeVar("SequencerType", bound=Sequencer)


class SequencerProxy(DeviceProxy[SequencerType]):
    async def update_parameters(
        self, sequence: SequencerInstruction, *args, **kwargs
    ) -> None:
        return await self.call_method(
            "update_parameters", *args, sequence=sequence, **kwargs
        )

    async def start_sequence(self) -> None:
        return await self.call_method("start_sequence")

    async def has_sequence_finished(self) -> bool:
        return await self.call_method("has_sequence_finished")

    async def get_trigger(self) -> Trigger:
        return await self.get_attribute("trigger")
