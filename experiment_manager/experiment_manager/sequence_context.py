import asyncio
import contextlib
from collections.abc import Coroutine, Awaitable
from copy import deepcopy
from typing import Generic, TypeVar, Self, Optional

from units import AnalogValue
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace


class SequenceContext:
    def __init__(self, variables: VariableNamespace[AnalogValue]):
        self.variables: VariableNamespace[AnalogValue] = variables


T = TypeVar("T")


class StepContext(Generic[T]):
    """Immutable context that contains the variables of a given step.

    This object contains the value of some variables, and it also contains the previous value of the variables since the
    last time this object history was reset.
    """
    def __init__(self) -> None:
        self._variables = VariableNamespace[T]()

        # This is a dictionary of variables that have changed since the last time this object was reset.
        # The key is the variable name, and the value is the previous value of the variable.
        self._variables_that_changed: dict[DottedVariableName, Optional[T]] = {}

    def clone(self) -> Self:
        return deepcopy(self)

    def update_variable(self, name: DottedVariableName, value: T) -> Self:
        clone = self.clone()
        if name in clone._variables_that_changed:
            # We keep the last previous value as the correct previous value
            pass
        else:
            clone._variables_that_changed[name] = clone._variables[name]
        clone._variables.update({name: value})
        return clone

    def reset_history(self) -> Self:
        clone = self.clone()
        clone._variables_that_changed = {}
        return clone

    @property
    def variables(self):
        return deepcopy(self._variables)


class SequenceTaskGroup:
    def __init__(self) -> None:
        self._hardware_task_group: asyncio.TaskGroup = asyncio.TaskGroup()
        self._database_task_group: asyncio.TaskGroup = asyncio.TaskGroup()
        self._exit_stack = contextlib.AsyncExitStack()

    def create_hardware_task(self, coro: Coroutine) -> asyncio.Task:
        return self._hardware_task_group.create_task(coro)

    def create_database_task(self, coro: Coroutine) -> Awaitable:
        return asyncio.shield(self._database_task_group.create_task(coro))

    async def __aenter__(self):
        await self._exit_stack.__aenter__()
        await self._exit_stack.enter_async_context(self._hardware_task_group)
        await self._exit_stack.enter_async_context(self._database_task_group)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
