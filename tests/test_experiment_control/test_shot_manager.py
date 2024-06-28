import logging
from collections.abc import Mapping
from typing import Any

import anyio
import anyio.to_process

from caqtus.device import DeviceName
from caqtus.experiment_control.sequence_runner.shots_manager import (
    ShotRunner,
    ShotCompiler,
    ShotManager,
    ShotRetryConfig,
)
from caqtus.shot_compilation import VariableNamespace
from caqtus.types.data import DataLabel, Data
from caqtus.utils.logging import caqtus_logger

logging.basicConfig(level=logging.INFO)

caqtus_logger.setLevel(logging.DEBUG)


def do_nothing():
    pass


class ShotRunnerMock(ShotRunner):
    async def run_shot(
        self, device_parameters: Mapping[DeviceName, Mapping[str, Any]], timeout: float
    ) -> Mapping[DataLabel, Data]:
        return {DataLabel("data"): 0}


class ShotCompilerMock(ShotCompiler):
    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        return {DeviceName("device"): {"param": 0}}, 1.0


def test_0():
    async def schedule_shots(scheduler):
        for shot in range(10):
            await scheduler.schedule_shot(VariableNamespace({"rep": shot}))

    shot_results = []

    async def collect_data(shots_data) -> list[Mapping[DataLabel, Data]]:
        async for shot in shots_data:
            shot_results.append(shot)
        return shot_results

    async def fun():
        shot_manager = ShotManager(
            ShotRunnerMock(), ShotCompilerMock(), ShotRetryConfig()
        )
        async with (
            shot_manager as data_output_stream,
            anyio.create_task_group() as data_tg,
            shot_manager.scheduler() as scheduler,
            anyio.create_task_group() as scheduler_tg,
        ):
            data_tg.start_soon(collect_data, data_output_stream)
            scheduler_tg.start_soon(schedule_shots, scheduler)

    anyio.run(fun, backend="trio")
    shot_indices = [shot_data.index for shot_data in shot_results]
    assert shot_indices == list(range(10))
