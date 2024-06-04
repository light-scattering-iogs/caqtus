import anyio

from caqtus.device.controller import DeviceController
from ._proxy import SequencerProxy
from .instructions import SequencerInstruction
from .runtime import Sequencer
from .trigger import SoftwareTrigger


class SequencerController(DeviceController):
    """Controls a sequencer during a shot."""

    async def run_shot(
        self,
        sequencer: SequencerProxy,
        /,
        sequence: SequencerInstruction,
        *args,
        **kwargs,
    ) -> None:
        await sequencer.update_parameters(sequence=sequence, *args, **kwargs)
        await self.start(sequencer)
        await self.wait_until_finished(sequencer)

    async def program(
        self, sequencer: Sequencer, sequence: SequencerInstruction
    ) -> None:
        await self.run_in_thread(sequencer.update_parameters, sequence=sequence)

    async def start(self, sequencer: SequencerProxy) -> None:
        trigger = await sequencer.get_trigger()
        if isinstance(trigger, SoftwareTrigger):
            await self.wait_all_devices_ready()
            await sequencer.start_sequence()
        else:
            await sequencer.start_sequence()
            await self.wait_all_devices_ready()

    async def wait_until_finished(self, sequencer: SequencerProxy) -> None:
        # We shield the task because we don't want the sequence to be stopped in the
        # middle with possibly dangerous values on the sequencer channels.
        with anyio.CancelScope(shield=True):
            while not await sequencer.has_sequence_finished():
                await self.sleep(0)
