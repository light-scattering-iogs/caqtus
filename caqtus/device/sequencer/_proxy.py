import contextlib
from typing import TypeVar

from caqtus.device.remote import DeviceProxy
from .instructions import SequencerInstruction
from .runtime import Sequencer
from .trigger import Trigger
from ..remote.rpc import RPCClient, Proxy

SequencerType = TypeVar("SequencerType", bound=Sequencer)


class SequencerProxy(DeviceProxy[SequencerType]):
    @contextlib.asynccontextmanager
    async def program_sequence(self, sequence: SequencerInstruction):
        async with self.call_method_proxy_result(
            "program_sequence", sequence
        ) as sequence_proxy:
            yield ProgrammedSequenceProxy(self._rpc_client, sequence_proxy)

    async def get_trigger(self) -> Trigger:
        return await self.get_attribute("trigger")


class ProgrammedSequenceProxy:
    def __init__(self, rpc_client: RPCClient, proxy: Proxy):
        self._rpc_client = rpc_client
        self._proxy = proxy

    @contextlib.asynccontextmanager
    async def run(self):
        async with (
            self._rpc_client.call_method_proxy_result("run") as run_cm_proxy,
            self._rpc_client.async_context_manager(run_cm_proxy) as status_proxy,
        ):
            yield SequenceStatusProxy(self._rpc_client, status_proxy)


class SequenceStatusProxy:
    def __init__(self, rpc_client: RPCClient, proxy: Proxy):
        self._rpc_client = rpc_client
        self._proxy = proxy

    async def is_finished(self) -> bool:
        return await self._rpc_client.call_method(self._proxy, "is_finished")
