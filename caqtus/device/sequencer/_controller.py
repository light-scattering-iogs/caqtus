import anyio

from caqtus.device.controller import DeviceController, run_in_thread, sleep
from caqtus.device.sequencer import Sequencer, SoftwareTrigger
from .instructions import SequencerInstruction


class SequencerController(DeviceController[Sequencer]):
    """Controls a sequencer during a shot."""

    async def run_shot(self, device: Sequencer, sequence: SequencerInstruction) -> None:
        await run_in_thread(device.update_parameters, sequence=sequence)
        if isinstance(device.get_trigger(), SoftwareTrigger):
            self.signal_ready()
            await self.wait_all_devices_ready()
            device.start_sequence()
        else:
            await run_in_thread(device.start_sequence)
            self.signal_ready()
        with anyio.CancelScope(shield=True):
            while not await run_in_thread(device.has_sequence_finished):
                await sleep(0)
