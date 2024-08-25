import contextlib
import threading
from collections.abc import Mapping
from typing import Any

import anyio

from caqtus.device import DeviceName
from caqtus.experiment_control._shot_compiler import ShotCompilerProtocol
from caqtus.experiment_control._shot_runner import ShotRunnerProtocol
from caqtus.experiment_control.device_manager_extension import DeviceManagerExtension
from caqtus.experiment_control.sequence_runner.sequence_manager import run_sequence
from caqtus.session import State
from caqtus.shot_compilation import VariableNamespace
from caqtus.types.data import DataLabel, Data


class ShotRunnerMock(ShotRunnerProtocol):
    async def run_shot(
        self, device_parameters: Mapping[DeviceName, Mapping[str, Any]], timeout: float
    ) -> Mapping[DataLabel, Data]:
        return {DataLabel("data"): 0}


class ShotCompilerMock(ShotCompilerProtocol):
    def compile_initialization_parameters(
        self,
    ) -> Mapping[DeviceName, Mapping[str, Any]]:
        return {DeviceName("device"): {"param": 0}}

    async def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        await anyio.sleep(0)
        return {DeviceName("device"): {"param": 0}}, 1.0


def create_shot_compiler_mock(sequence_context, device_manager_extension):
    return ShotCompilerMock()


@contextlib.asynccontextmanager
async def create_shot_runner_mock(
    sequence_context, shot_compiler, device_manager_extension
):
    yield ShotRunnerMock()


async def test_successful_sequence(anyio_backend, session_maker, draft_sequence):
    await run_sequence(
        draft_sequence,
        session_maker,
        threading.Event(),
        None,
        None,
        None,
        DeviceManagerExtension(),
        create_shot_runner_mock,
        create_shot_compiler_mock,
    )

    with session_maker.session() as session:
        sequence = session.get_sequence(draft_sequence)
        assert sequence.get_state() == State.FINISHED
        assert (
            len(list(sequence.get_shots()))
            == sequence.get_iteration_configuration().expected_number_shots()
        )
