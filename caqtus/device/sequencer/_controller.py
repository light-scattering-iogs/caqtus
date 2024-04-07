import anyio

from caqtus.device.controller import DeviceController, run_in_thread, sleep
from caqtus.device.sequencer import Sequencer, SoftwareTrigger
from .instructions import SequencerInstruction


class SequencerController(DeviceController):
    """Controls a sequencer during a shot."""

    async def run_shot(
        self, sequencer: Sequencer, /, sequence: SequencerInstruction
    ) -> None:
        await self.program(sequencer, sequence)
        await self.start(sequencer)
        await self.wait_until_finished(sequencer)

    @staticmethod
    async def program(sequencer: Sequencer, sequence: SequencerInstruction) -> None:
        await run_in_thread(sequencer.update_parameters, sequence=sequence)

    async def start(self, sequencer: Sequencer) -> None:
        if isinstance(sequencer.get_trigger(), SoftwareTrigger):
            self.signal_ready()
            await self.wait_all_devices_ready()
            sequencer.start_sequence()
        else:
            await run_in_thread(sequencer.start_sequence)
            self.signal_ready()

    @staticmethod
    async def wait_until_finished(sequencer: Sequencer) -> None:
        # We shield the task because we don't want the sequence to be stopped in the
        # middle with possibly dangerous values on the sequencer channels.
        with anyio.CancelScope(shield=True):
            while not await run_in_thread(sequencer.has_sequence_finished):
                await sleep(0)
