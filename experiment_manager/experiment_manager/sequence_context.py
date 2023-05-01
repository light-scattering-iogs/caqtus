import asyncio
import contextlib
from collections.abc import Coroutine
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
            if name in clone._variables:
                if clone._variables[name] == value:
                    # No need to register the change if the value is the same
                    pass
                else:
                    clone._variables_that_changed[name] = clone._variables[name]
            else:
                clone._variables_that_changed[name] = None
        clone._variables.update({name: value})
        return clone

    def reset_history(self) -> Self:
        clone = self.clone()
        clone._variables_that_changed = {}
        return clone

    @property
    def variables(self):
        return deepcopy(self._variables)

    @property
    def updated_variables(self) -> set[DottedVariableName]:
        return set(self._variables_that_changed.keys())


class SequenceTaskGroup:
    """

    Each computation task must be associated with one and only one hardware task.
    """

    def __init__(self) -> None:
        self._task_group: asyncio.TaskGroup = asyncio.TaskGroup()
        self._exit_stack = contextlib.AsyncExitStack()
        self._hardware_tasks: set[asyncio.Task] = set()

        # Used to limit the number of computation tasks in advance with respect to the number of hardware tasks.
        # If we let computations run freely ahead, they will quickly fill up the memory with all the devices parameters.
        self._computation_heads_up = asyncio.Semaphore(25)

    def create_hardware_task(self, coro: Coroutine) -> asyncio.Task:
        async def wrapped():
            await coro
            self._computation_heads_up.release()
        task = self._task_group.create_task(wrapped())
        self._hardware_tasks.add(task)
        return task

    async def wait_shots_completed(self):
        await asyncio.gather(*self._hardware_tasks)
        self._hardware_tasks.clear()

    async def create_computation_task(self, coro: Coroutine) -> asyncio.Task:
        await self._computation_heads_up.acquire()
        return self._task_group.create_task(coro)

    def create_database_task(self, coro: Coroutine) -> asyncio.Task:
        return self._task_group.create_task(coro)

    async def __aenter__(self):
        await self._exit_stack.enter_async_context(self._task_group)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._exit_stack.aclose()
