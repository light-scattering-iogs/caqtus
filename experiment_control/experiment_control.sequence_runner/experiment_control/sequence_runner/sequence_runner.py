import asyncio
import logging
from collections.abc import Mapping
from concurrent.futures import Executor
from functools import singledispatchmethod
from threading import Thread, Event
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    TypeVar,
    Awaitable,
)

import numpy as np

from device.configuration import DeviceName, DeviceParameter
from device.runtime import RuntimeDevice
from duration_timer import DurationTimerLog
from experiment.configuration import (
    ExperimentConfig,
)
from experiment.session import ExperimentSessionMaker
from experiment_control.compute_device_parameters import (
    compute_shot_parameters,
    compute_parameters_on_variables_update,
)
from experiment_control.compute_device_parameters.image_analysis import (
    find_how_to_analyze_images,
    find_how_to_rearrange,
)
from parameter_types import AnalogValue, add_unit, get_unit, magnitude_in_unit
from sequence.configuration import (
    Step,
    SequenceSteps,
    ArangeLoop,
    LinspaceLoop,
    VariableDeclaration,
    ExecuteShot,
    OptimizationLoop,
    UserInputLoop,
    VariableRange,
    ShotConfiguration,
)
from sequence.runtime import SequencePath, Sequence, Shot, State
from units import Quantity, units, DimensionalityError
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace
from .device_context_manager import DeviceContextManager
from .devices_handler import (
    get_sequencers_in_use,
    get_cameras_in_use,
    get_tweezer_arrangers_in_use,
)
from .sequence_context import StepContext
from .sequence_manager import SequenceManager, ShotParameters, ShotDeviceParameters, ShotMetadata
from .user_input_loop.exec_user_input import ExecUserInput
from .user_input_loop.input_widget import RawVariableRange, EvaluatedVariableRange

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

WATCH_FOR_INTERRUPTION_INTERVAL = 0.1  # seconds


# This is the number of processes that can run in parallel to compile the shots.
NUMBER_WORKERS = 8

PARAMETER_QUEUE_SIZE = 10
DEVICE_PARAMETER_QUEUE_SIZE = 8
STORAGE_QUEUE_SIZE = 10


class SequenceRunnerThread(Thread):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
        must_interrupt: Event,
    ):
        super().__init__(name=f"thread_{str(sequence_path)}")
        self._sequence_manager = SequenceManager(
            experiment_config_name, sequence_path, session_maker
        )
        self._devices: dict[DeviceName, RuntimeDevice] = {}

        # We watch this event while running the sequence and raise SequenceInterrupted if it becomes set.
        self._must_interrupt = must_interrupt

        # self._shot_parameters_queue: asyncio.Queue[ShotParameters] = asyncio.Queue(
        #     maxsize=PARAMETER_QUEUE_SIZE
        # )
        #
        # # This queue contains the information of the next shots to execute. Items are added when new shot parameters are
        # # computed, and consumed when the shots are executed.
        # self._device_parameters_queue: asyncio.Queue[
        #     ShotDeviceParameters
        # ] = asyncio.Queue(maxsize=DEVICE_PARAMETER_QUEUE_SIZE)
        #
        # # When a shot is finished, its data is added to this queue. The data is then saved to the database.
        # self._storage_queue: asyncio.Queue[ShotMetadata] = asyncio.Queue(
        #     maxsize=STORAGE_QUEUE_SIZE
        # )
        #
        # # This stack is used to ensure that proper cleanup is done when an error occurs.
        # # For now, it is only used to close the devices properly.
        # self._shutdown_stack = contextlib.ExitStack()
        #
        # # This executor is used to run the computations that are done in the background. Using a ProcessPoolExecutor
        # # allows to run them in parallel unlike a ThreadPoolExecutor that runs them concurrently.
        # self._computation_executor = ProcessPoolExecutor()
        #
        # self._image_analysis_flow = {}
        # self._current_shot = 0
        # self._device_handler = DevicesHandler()

    def run(self):
        try:
            with self._sequence_manager:
                self.run_sequence()
        except Exception:
            logger.error("An error occurred while running the sequence", exc_info=True)
            raise

    async def prepare(self):


        logger.debug(devices)

        for device_name, device in devices.items():
            # We initialize the devices through the stack to unsure that they are closed if an error occurs.
            self._devices[device_name] = self._shutdown_stack.enter_context(
                DeviceContextManager(device)
            )

        async with asyncio.TaskGroup() as task_group:
            for device in self._devices.values():
                task_group.create_task(asyncio.to_thread(initialize_device, device))

        self._device_handler.sequencers = get_sequencers_in_use(
            self._devices, self._experiment_config
        )
        self._device_handler.cameras = get_cameras_in_use(
            self._devices, self._experiment_config
        )
        self._device_handler.tweezer_arrangers = get_tweezer_arrangers_in_use(
            self._devices, self._experiment_config
        )

        with self._session.activate() as session:
            self._sequence.set_state(State.RUNNING, session)

    def run_sequence(self):
        """Run the sequence.

        This function will first run the sequence header used to populate the context with constants, then it will run
        the sequence program containing the shots.
        """

        context = StepContext[AnalogValue]()

        # async with asyncio.TaskGroup() as task_group:
        #     watch_for_interruption = task_group.create_task(
        #         self.watch_for_interruption()
        #     )
        #     compile_shots = task_group.create_task(self.compile_shots())
        #     run_shots = task_group.create_task(self.run_shots())
        #     store_shots = task_group.create_task(self.store_shots())
        context = self.run_step(
            self._sequence_manager.experiment_config.header, context
        )
        _ = self.run_step(self._sequence_manager.sequence_config.program, context)
        # await self._shot_parameters_queue.join()
        # await self._device_parameters_queue.join()
        # await self._storage_queue.join()
        # compile_shots.cancel()
        # run_shots.cancel()
        # store_shots.cancel()
        # watch_for_interruption.cancel()

    async def watch_for_interruption(self):
        """Raise SequenceInterrupted if the sequence must be interrupted."""

        while True:
            await asyncio.sleep(WATCH_FOR_INTERRUPTION_INTERVAL)
            if self._must_interrupt.is_set():
                raise SequenceInterruptedException()

    async def compile_shots(self) -> None:
        async with asyncio.TaskGroup() as task_group:
            for _ in range(NUMBER_WORKERS):
                task_group.create_task(self._get_and_compile_shot())

    async def _get_and_compile_shot(self) -> None:
        while True:
            shot_parameters = await self._shot_parameters_queue.get()
            device_parameters = await self.compute_shot_parameters(
                shot_parameters,
                self._computation_executor,
            )
            await self._device_parameters_queue.put(device_parameters)
            self._shot_parameters_queue.task_done()

    async def run_shots(self) -> None:
        while True:
            device_parameters = await self._device_parameters_queue.get()
            shot_data = await self.do_shot_with_retry(device_parameters)
            self._device_parameters_queue.task_done()
            await self._storage_queue.put(shot_data)

    async def store_shots(self) -> None:
        while True:
            shot_data = await self._storage_queue.get()
            await self.store_shot(shot_data)
            self._storage_queue.task_done()

    @singledispatchmethod
    def run_step(self, step: Step, context: StepContext) -> StepContext:
        """Execute a given step of the sequence

        This function should be implemented for each Step type that can be run on the
        experiment.

        Args:
            step: the step of the sequence currently executed
            context: Contains the values of the variables before this step.

        Returns:
            A new context object that contains the values of the variables after this step. This context object must be
            a new object.
        """

        raise NotImplementedError(f"run_step is not implemented for {type(step)}")

    @run_step.register
    def _(
        self,
        steps: SequenceSteps,
        context: StepContext,
    ) -> StepContext:
        """Execute the steps of a SequenceSteps.

        This function executes the child steps of a SequenceSteps in order. The context is updated after each step and
        the updated context is passed to the next step.
        """

        for step in steps.children:
            context = self.run_step(step, context)
        return context

    @run_step.register
    def _(
        self,
        declaration: VariableDeclaration,
        context: StepContext,
    ) -> StepContext:
        """Execute a VariableDeclaration step.

        This function evaluates the expression of the declaration and updates the value of the variable in the context.
        """

        value = Quantity(declaration.expression.evaluate(context.variables | units))
        return context.update_variable(declaration.name, value)

    @run_step.register
    def _(
        self,
        arange_loop: ArangeLoop,
        context: StepContext,
    ):
        """Loop over a variable in a numpy arange like loop"""

        variables = context.variables | units

        start = Quantity(arange_loop.start.evaluate(variables))
        stop = Quantity(arange_loop.stop.evaluate(variables))
        step = Quantity(arange_loop.step.evaluate(variables))
        unit = start.units

        start = start.to(unit)
        try:
            stop = stop.to(unit)
        except DimensionalityError:
            raise ValueError(
                f"Stop units of arange loop '{arange_loop.name}' ({stop.units}) is not"
                f" compatible with start units ({unit})"
            )
        try:
            step = step.to(unit)
        except DimensionalityError:
            raise ValueError(
                f"Step units of arange loop '{arange_loop.name}' ({step.units}) are not"
                f" compatible with start units ({unit})"
            )

        for value in np.arange(start.magnitude, stop.magnitude, step.magnitude):
            context = context.update_variable(arange_loop.name, value * unit)
            for step in arange_loop.children:
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(
        self,
        linspace_loop: LinspaceLoop,
        context: StepContext,
    ):
        """Loop over a variable in a numpy linspace like loop"""

        variables = context.variables | units

        try:
            start = Quantity(linspace_loop.start.evaluate(variables))
        except Exception as error:
            raise ValueError(
                f"Could not evaluate start of linspace loop {linspace_loop.name}"
            ) from error
        unit = start.units
        try:
            stop = Quantity(linspace_loop.stop.evaluate(variables))
        except Exception as error:
            raise ValueError(
                f"Could not evaluate stop of linspace loop {linspace_loop.name}"
            ) from error
        try:
            stop = stop.to(unit)
        except DimensionalityError:
            raise ValueError(
                f"Stop units of linspace loop '{linspace_loop.name}' ({stop.units}) is not"
                f" compatible with start units ({unit})"
            )
        num = int(linspace_loop.num)

        for value in np.linspace(start.magnitude, stop.magnitude, num):
            context = context.update_variable(linspace_loop.name, value * unit)
            for step in linspace_loop.children:
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, shot: ExecuteShot, context: StepContext) -> StepContext:
        """Compute the parameters of a shot and push them to the queue to be executed."""

        if self._must_interrupt.is_set():
            self._sequence_manager.interrupt_sequence()
        self._sequence_manager.schedule_shot(shot.name, context)
        return context.reset_history()

    async def compute_shot_parameters(
        self, shot_parameters: ShotParameters, executor: Executor
    ) -> ShotDeviceParameters:
        with DurationTimerLog(
            logger,
            f"Shot parameters computation {shot_parameters.index}",
            display_start=True,
        ):
            # For some reason, ExperimentConfiguration cannot be pickled when using a ProcessPoolExecutor, so we pass
            # the yaml representation of the configuration instead.
            compute_change_params_task = async_run_in_executor(
                executor,
                _wrap_compute_parameters_on_variables_update,
                shot_parameters.context.updated_variables,
                shot_parameters.context.variables,
                self._experiment_config_yaml,
            )

            compute_static_params_task = async_run_in_executor(
                executor,
                _wrap_compute_shot_parameters,
                self._experiment_config_yaml,
                self._sequence_config.shot_configurations[shot_parameters.name],
                shot_parameters.context.variables,
            )
            change_params = await compute_change_params_task
            shot_params = await compute_static_params_task

            return ShotDeviceParameters(
                name=shot_parameters.name,
                context=shot_parameters.context,
                index=shot_parameters.index,
                change_parameters=change_params,
                static_parameters=shot_params,
            )

    @run_step.register
    async def _(self, loop: UserInputLoop, context: StepContext) -> StepContext:
        """Repeat its child steps while asking the user the value of some variables."""

        evaluated_variable_ranges = evaluate_variable_ranges(
            loop.iteration_variables, context.variables | units
        )
        raw_variable_ranges = strip_unit_from_variable_ranges(evaluated_variable_ranges)
        variable_units = {
            name: value.unit for name, value in raw_variable_ranges.items()
        }

        runner = ExecUserInput(
            title=str(self._sequence.path),
            variable_ranges=raw_variable_ranges,
        )

        async with asyncio.TaskGroup() as background_task_group:
            task = background_task_group.create_task(asyncio.to_thread(runner.run))

            child_step_index = 0
            while not task.done():
                raw_values = runner.get_current_values()
                for variable_name, raw_value in raw_values.items():
                    minimum = evaluated_variable_ranges[variable_name].minimum
                    maximum = evaluated_variable_ranges[variable_name].maximum
                    value = add_unit(raw_value, variable_units[variable_name])
                    if not (minimum <= value <= maximum):
                        raise ValueError(
                            f"Value {value} for variable {variable_name} is not in the "
                            f"range [{minimum}, {maximum}]"
                        )
                    context = context.update_variable(variable_name, value)

                if child_step_index < len(loop.children):
                    context = await self.run_step(
                        loop.children[child_step_index], context
                    )
                    child_step_index += 1
                else:
                    child_step_index = 0
                await self._device_parameters_queue.join()
        return context

    @run_step.register
    async def _(
        self,
        optimization_loop: OptimizationLoop,
        context: StepContext,
    ):
        raise NotImplementedError

    async def store_shot(
        self,
        shot_data: ShotMetadata,
    ) -> Shot:
        with DurationTimerLog(
            logger, f"Saving shot {shot_data.index}", display_start=True
        ):
            return await async_run_in_executor(
                self._computation_executor,
                save_shot,
                self._sequence,
                shot_data,
                self._session_maker,
            )


def save_shot(
    sequence: Sequence,
    shot_data: ShotMetadata,
    session_maker: ExperimentSessionMaker,
) -> Shot:
    with session_maker() as session:
        params = {
            name: value for name, value in shot_data.variables.to_flat_dict().items()
        }
        return sequence.create_shot(
            name=shot_data.name,
            start_time=shot_data.start_time,
            end_time=shot_data.end_time,
            parameters=params,
            measures=shot_data.data,
            experiment_session=session,
        )


def initialize_device(device: RuntimeDevice):
    """Initialize a device.

    The goal of this function is to provide a more informative error message when a device fails to initialize.
    """
    try:
        device.initialize()
        logger.info(f"Device '{device.get_name()}' started.")
    except Exception as error:
        raise RuntimeError(f"Could not start device '{device.get_name()}'") from error


def _wrap_compute_parameters_on_variables_update(
    updated_variables: set[DottedVariableName],
    variables: VariableNamespace,
    experiment_config_yaml: str,
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    experiment_config = ExperimentConfig.from_yaml(experiment_config_yaml)
    return compute_parameters_on_variables_update(
        updated_variables, variables, experiment_config
    )


def _wrap_compute_shot_parameters(
    experiment_config_yaml: str,
    shot_config: ShotConfiguration,
    variables: VariableNamespace,
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    experiment_config = ExperimentConfig.from_yaml(experiment_config_yaml)
    return compute_shot_parameters(experiment_config, shot_config, variables)


def evaluate_variable_ranges(
    variable_ranges: Mapping[DottedVariableName, VariableRange],
    context_variables: Mapping[DottedVariableName, Any],
) -> dict[DottedVariableName, EvaluatedVariableRange]:
    """Replace expressions in variable ranges with their real values."""

    evaluated_variable_ranges: dict[DottedVariableName, EvaluatedVariableRange] = {}
    for variable_name, variable_range in variable_ranges.items():
        initial_value = variable_range.initial_value.evaluate(context_variables)

        first_bound = variable_range.first_bound.evaluate(context_variables)
        second_bound = variable_range.second_bound.evaluate(context_variables)

        minimum = min(first_bound, second_bound)
        maximum = max(first_bound, second_bound)
        evaluated_range = EvaluatedVariableRange(
            initial_value=initial_value,
            minimum=minimum,
            maximum=maximum,
        )
        evaluated_variable_ranges[variable_name] = evaluated_range
    return evaluated_variable_ranges


def strip_unit_from_variable_ranges(
    variable_ranges: dict[DottedVariableName, EvaluatedVariableRange],
) -> dict[DottedVariableName, RawVariableRange]:
    """Replace expressions in variable ranges with their real values."""

    raw_variable_ranges: dict[DottedVariableName, RawVariableRange] = {}
    for variable_name, variable_range in variable_ranges.items():
        initial_value = variable_range.initial_value
        unit = get_unit(initial_value)
        initial_value = magnitude_in_unit(initial_value, unit)

        minimum = variable_range.minimum
        minimum = magnitude_in_unit(minimum, unit)
        maximum = variable_range.maximum
        maximum = magnitude_in_unit(maximum, unit)

        evaluated_range = RawVariableRange(
            initial_value=initial_value,
            minimum=minimum,
            maximum=maximum,
            unit=unit,
        )
        raw_variable_ranges[variable_name] = evaluated_range
    return raw_variable_ranges


_T = TypeVar("_T")


def async_run_in_executor(
    executor: Executor, func: Callable[..., _T], *args
) -> Awaitable[_T]:
    """Schedula a function to run in an executor and return an awaitable for its result."""

    return asyncio.get_running_loop().run_in_executor(executor, func, *args)


# This exception is used to interrupt the sequence and inherit from BaseException to prevent it from being caught
# accidentally.
class SequenceInterruptedException(BaseException):
    pass
