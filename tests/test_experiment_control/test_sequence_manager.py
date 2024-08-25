import contextlib
from collections.abc import Mapping
from typing import Any

import anyio

from caqtus.device import DeviceName
from caqtus.experiment_control._shot_compiler import ShotCompilerProtocol
from caqtus.experiment_control._shot_primitives import DeviceParameters, ShotParameters
from caqtus.experiment_control._shot_runner import ShotRunnerProtocol, ShotRunnerFactory
from caqtus.experiment_control.device_manager_extension import DeviceManagerExtension
from caqtus.experiment_control.sequence_runner.sequence_manager import run_sequence
from caqtus.session import State
from caqtus.types.data import DataLabel, Data


class ShotRunnerMock(ShotRunnerProtocol):
    async def run_shot(
        self, shot_parameters: DeviceParameters
    ) -> Mapping[DataLabel, Data]:
        return {DataLabel("data"): 0}

    @classmethod
    @contextlib.asynccontextmanager
    async def create(cls, sequence_context, shot_compiler, device_manager_extension):
        yield ShotRunnerMock()


class ShotCompilerMock(ShotCompilerProtocol):
    def compile_initialization_parameters(
        self,
    ) -> Mapping[DeviceName, Mapping[str, Any]]:
        return {DeviceName("device"): {"param": 0}}

    async def compile_shot(
        self, shot_parameters: ShotParameters
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        await anyio.sleep(0)
        return {DeviceName("device"): {"param": 0}}, 1.0

    @classmethod
    def create(cls, sequence_context, device_manager_extension):
        return cls()


async def test_successful_sequence(anyio_backend, session_maker, draft_sequence):
    await run_sequence(
        draft_sequence,
        session_maker,
        None,
        None,
        None,
        DeviceManagerExtension(),
        ShotRunnerMock.create,
        ShotCompilerMock.create,
    )

    with session_maker.session() as session:
        sequence = session.get_sequence(draft_sequence)
        assert sequence.get_state() == State.FINISHED
        assert (
            len(list(sequence.get_shots()))
            == sequence.get_iteration_configuration().expected_number_shots()
        )


class InterruptShotRunner(ShotRunnerProtocol):

    def __init__(
        self,
        shot_runner: ShotRunnerProtocol,
        shot_to_interrupt: int,
        cancel_scope: anyio.CancelScope,
    ):
        self.shot_runner = shot_runner
        self.shot_to_interrupt = shot_to_interrupt
        self.cancel_scope = cancel_scope

    async def run_shot(
        self, shot_parameters: DeviceParameters
    ) -> Mapping[DataLabel, Data]:

        if shot_parameters.index == self.shot_to_interrupt:
            self.cancel_scope.cancel()

        return await self.shot_runner.run_shot(shot_parameters)

    @classmethod
    def create(
        cls,
        factory: ShotRunnerFactory,
        shot_to_interrupt: int,
        cancel_scope: anyio.CancelScope,
    ):
        @contextlib.asynccontextmanager
        async def _create(sequence_context, shot_compiler, device_manager_extension):
            async with factory(
                sequence_context, shot_compiler, device_manager_extension
            ) as runner:
                yield cls(runner, shot_to_interrupt, cancel_scope)

        return _create


async def test_sequence_interruption(anyio_backend, session_maker, draft_sequence):
    with anyio.CancelScope() as cancel_scope:
        await run_sequence(
            draft_sequence,
            session_maker,
            None,
            None,
            None,
            DeviceManagerExtension(),
            InterruptShotRunner.create(ShotRunnerMock.create, 7, cancel_scope),
            ShotCompilerMock.create,
        )

    with session_maker.session() as session:
        sequence = session.get_sequence(draft_sequence)
        assert sequence.get_state() == State.INTERRUPTED
        assert len(list(sequence.get_shots())) == 7
