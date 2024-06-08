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
    shot_manager = ShotManager(ShotRunnerMock(), ShotCompilerMock(), ShotRetryConfig())

    async def schedule_shots(shot_manager: ShotManager):
        async with shot_manager.start_scheduling():
            for shot in range(1000):
                await shot_manager.schedule_shot(VariableNamespace({"rep": shot}))

    shot_results = []

    async def collect_data(shot_manager) -> list[Mapping[DataLabel, Data]]:
        async with shot_manager.run() as shots_data:
            async for shot in shots_data:
                shot_results.append(shot)
        return shot_results

    async def fun():
        async with anyio.create_task_group() as tg:
            tg.start_soon(collect_data, shot_manager)
            tg.start_soon(schedule_shots, shot_manager)

    anyio.run(fun)
    assert len(shot_results) == 1000
