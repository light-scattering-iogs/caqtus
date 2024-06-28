import time
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
    length = 100

    async def schedule_shots(scheduler):
        for shot in range(length):
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

    t0 = time.perf_counter()
    anyio.run(fun, backend="trio")
    t1 = time.perf_counter()
    print(f"Time taken: {t1 - t0:.2f} s")
    shot_indices = [shot_data.index for shot_data in shot_results]
    assert shot_indices == list(range(length))
