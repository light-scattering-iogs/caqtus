import contextlib
from typing import TypeVar

from caqtus.device.remote import DeviceProxy, AsyncConverter
from caqtus.shot_compilation.timed_instructions import TimedInstruction
from .runtime import Sequencer
from .trigger import Trigger
from ..remote.rpc import Proxy

SequencerType = TypeVar("SequencerType", bound=Sequencer)


class SequencerProxy(DeviceProxy[SequencerType]):
    @contextlib.asynccontextmanager
    async def program_sequence(self, sequence: TimedInstruction):
        async with self.call_method_proxy_result(
            "program_sequence", sequence
        ) as sequence_proxy:
            yield ProgrammedSequenceProxy(self.async_converter, sequence_proxy)

    async def get_trigger(self) -> Trigger:
        return await self.get_attribute("trigger")


class ProgrammedSequenceProxy:
    def __init__(self, async_converter: AsyncConverter, proxy: Proxy):
        self._async_converter = async_converter
        self._proxy = proxy

    @contextlib.asynccontextmanager
    async def run(self):
        async with (
            self._async_converter.call_method_proxy_result(
                self._proxy, "run"
            ) as run_cm_proxy,
            self._async_converter.async_context_manager(run_cm_proxy) as status_proxy,
        ):
            yield SequenceStatusProxy(self._async_converter, status_proxy)


class SequenceStatusProxy:
    def __init__(self, async_converter: AsyncConverter, proxy: Proxy):
        self._async_converter = async_converter
        self._proxy = proxy

    async def is_finished(self) -> bool:
        return await self._async_converter.call_method(self._proxy, "is_finished")
