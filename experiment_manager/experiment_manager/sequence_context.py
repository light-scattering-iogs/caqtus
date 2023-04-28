import asyncio
import contextlib
from collections.abc import Coroutine
from copy import deepcopy
from typing import Generic, TypeVar, Self

from units import AnalogValue
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace


class SequenceContext:
    def __init__(self, variables: VariableNamespace[AnalogValue]):
        self.variables: VariableNamespace[AnalogValue] = variables


T = TypeVar("T")


class StepContext(Generic[T]):
    def __init__(self, variables: VariableNamespace[T]):
        self._variables = variables

    def clone(self) -> Self:
        return deepcopy(self)

    def update_variable(self, name: DottedVariableName, value: T) -> Self:
        clone = self.clone()
        clone._variables.update({name: value})
        return clone

    @property
    def variables(self):
        return deepcopy(self._variables)


class SequenceTaskGroup:
    def __init__(self) -> None:
        self._hardware_task_group: asyncio.TaskGroup = asyncio.TaskGroup()
        self._exit_stack = contextlib.AsyncExitStack()

    def create_hardware_task(self, coro: Coroutine) -> asyncio.Task:
        return self._hardware_task_group.create_task(coro)

    async def __aenter__(self):
        await self._exit_stack.__aenter__()
        await self._exit_stack.enter_async_context(self._hardware_task_group)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
