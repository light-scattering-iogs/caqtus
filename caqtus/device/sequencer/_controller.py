import dataclasses
from typing import TypeVar

import anyio
import anyio.to_thread

from caqtus.device.controller import DeviceController
from caqtus.device.sequencer import Sequencer, SoftwareTrigger
from .instructions import SequencerInstruction

SequencerType = TypeVar("SequencerType", bound=Sequencer)


class SequencerShotParameters(dataclasses.dataclass):
    """Parameters for running a shot on a sequencer."""

    sequence: SequencerInstruction


class SequencerController(DeviceController[SequencerType]):
    """Controls a sequencer during a shot."""

    async def run_shot(self, shot_parameters: SequencerShotParameters) -> None:
        await anyio.to_thread.run_sync(
            self.device.update_parameters, shot_parameters.sequence
        )
        if isinstance(self.device.get_trigger(), SoftwareTrigger):
            self.signal_ready()
            await self.wait_all_devices_ready()
            self.device.start_sequence()
        else:
            await anyio.to_thread.run_sync(self.device.start_sequence)
            self.signal_ready()
        with anyio.CancelScope(shield=True):
            while not await anyio.to_thread.run_sync(self.device.has_sequence_finished):
                await anyio.sleep(0)
