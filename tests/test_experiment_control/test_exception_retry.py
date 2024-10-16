from datetime import datetime

import pytest

from caqtus.device._controller import DeviceError
from caqtus.experiment_control.sequence_execution.shots_manager import (
    ShotData,
    _run_shot_with_retry,
    retry_condition,
)
from caqtus.types._parameter_namespace import VariableNamespace
from caqtus.types.recoverable_exceptions import ShotAttemptsExceededError


@pytest.fixture
def shot_data():
    return ShotData(
        index=0,
        start_time=datetime.now(),
        end_time=datetime.now(),
        variables=VariableNamespace(),
        data={},
    )


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_successful(anyio_backend, shot_data):
    async def successful_shot():
        return shot_data

    result = await _run_shot_with_retry(successful_shot, lambda exc: False, 1)
    assert result == shot_data


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_single_failure(anyio_backend, shot_data):
    index = 0

    async def failing_shot():
        nonlocal index
        index += 1
        if index == 1:
            try:
                raise DeviceError("Error") from TimeoutError("Timeout")
            except DeviceError as exc:
                raise ExceptionGroup("err", [exc])  # noqa: B904
        return shot_data

    result = await _run_shot_with_retry(
        failing_shot, retry_condition((TimeoutError,)), 2
    )
    assert result == shot_data
    assert index == 2


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_repeat_failure(anyio_backend, shot_data):
    async def failing_shot():
        try:
            raise DeviceError("Error") from TimeoutError("Timeout")
        except DeviceError as exc:
            raise ExceptionGroup("err", [exc])  # noqa: B904

    with pytest.raises(ShotAttemptsExceededError):
        await _run_shot_with_retry(failing_shot, retry_condition((TimeoutError,)), 1)


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_non_retriable_exception(anyio_backend, shot_data):
    async def failing_shot():
        raise RuntimeError("Error")

    with pytest.raises(RuntimeError):
        await _run_shot_with_retry(failing_shot, retry_condition((TimeoutError,)), 1)


@pytest.mark.parametrize("anyio_backend", ["trio"])
async def test_non_retriable_exception_group(anyio_backend, shot_data):
    async def failing_shot():
        raise ExceptionGroup("err", [RuntimeError("Error")])

    with pytest.raises(ExceptionGroup):
        await _run_shot_with_retry(failing_shot, retry_condition((TimeoutError,)), 1)
