import contextlib
import logging
from collections.abc import Mapping
from typing import Any, Never

import anyio
import anyio.to_process
import pytest

from caqtus.device import DeviceName
from caqtus.experiment_control.sequence_runner.shots_manager import (
    ShotRunnerProtocol,
    ShotCompilerProtocol,
    ShotManager,
    ShotRetryConfig,
    ShotScheduler,
    ShotData,
)
from caqtus.shot_compilation import VariableNamespace
from caqtus.types.data import DataLabel, Data
from caqtus.utils.logging import caqtus_logger

logging.basicConfig(level=logging.INFO)

caqtus_logger.setLevel(logging.DEBUG)


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

    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        return {DeviceName("device"): {"param": 0}}, 1.0


async def schedule_shots(
    scheduler_cm: contextlib.AbstractAsyncContextManager[ShotScheduler],
    number_of_shots: int,
):
    async with scheduler_cm as scheduler:
        for shot in range(number_of_shots):
            await scheduler.schedule_shot(VariableNamespace({"rep": shot}))


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_success(anyio_backend):
    length = 10

    shot_results = []

    async def collect_data(data_cm) -> list[ShotData]:
        async with data_cm as shots_data:
            async for shot in shots_data:
                shot_results.append(shot)
        return shot_results

    async with (
        ShotManager(ShotRunnerMock(), ShotCompilerMock(), ShotRetryConfig()) as (
            scheduler_cm,
            data_stream_cm,
        ),
        anyio.create_task_group() as tg,
    ):
        tg.start_soon(collect_data, data_stream_cm)
        tg.start_soon(schedule_shots, scheduler_cm, length)

    shot_indices = [shot_data.index for shot_data in shot_results]
    assert shot_indices == list(range(length))


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_consumption_failure(anyio_backend):
    length = 10

    shot_results = []

    async def collect_data(data_cm) -> Never:
        async with data_cm as shots_data:
            async for shot in shots_data:
                shot_results.append(shot)
            raise RuntimeError("Error")

    exception_raised = False

    try:
        async with (
            ShotManager(ShotRunnerMock(), ShotCompilerMock(), ShotRetryConfig()) as (
                scheduler_cm,
                data_stream_cm,
            ),
            anyio.create_task_group() as tg,
        ):
            tg.start_soon(collect_data, data_stream_cm)
            tg.start_soon(schedule_shots, scheduler_cm, length)

        shot_indices = [shot_data.index for shot_data in shot_results]
        assert shot_indices == list(range(length))
    except* RuntimeError:
        exception_raised = True
    assert exception_raised
