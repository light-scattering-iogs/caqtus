from caqtus.shot_compilation.timed_instructions import TimedInstruction
from ._proxy import SequencerProxy, SequenceStatusProxy
from .trigger import SoftwareTrigger
from .._controller import DeviceController


class SequencerController(DeviceController):
    """Controls a sequencer during a shot."""

    async def run_shot(
        self,
        sequencer: SequencerProxy,
        /,
        sequence: TimedInstruction,
        *args,
        **kwargs,
    ) -> None:
        trigger = await sequencer.get_trigger()
        async with sequencer.program_sequence(sequence) as programmed_sequence:
            if isinstance(trigger, SoftwareTrigger):
                await self.wait_all_devices_ready()
                async with programmed_sequence.run() as sequence_status:
                    await self.wait_until_finished(sequence_status)
            else:
                async with programmed_sequence.run() as sequence_status:
                    await self.wait_all_devices_ready()
                    await self.wait_until_finished(sequence_status)

    async def wait_until_finished(self, status: SequenceStatusProxy) -> None:
        while not await status.is_finished():
            await self.sleep(0)
