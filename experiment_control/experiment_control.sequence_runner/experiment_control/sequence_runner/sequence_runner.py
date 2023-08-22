import asyncio
import contextlib
import datetime
import logging
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, Executor
from functools import singledispatchmethod
from threading import Thread, Event
from typing import (
    TYPE_CHECKING,
    Any,
    NamedTuple,
    Callable,
    TypeVar,
    Awaitable,
)

import numpy as np

from aod_tweezer_arranger.configuration import AODTweezerArrangerConfiguration
from camera.runtime import CameraTimeoutError
from data_types import Data, DataLabel
from device.configuration import DeviceName, DeviceParameter
from device.runtime import RuntimeDevice
from duration_timer import DurationTimer, DurationTimerLog
from experiment.configuration import (
    CameraConfiguration,
    ExperimentConfig,
)
from experiment.session import ExperimentSessionMaker
from experiment_control.compute_device_parameters import (
    compute_shot_parameters,
    get_devices_initialization_parameters,
    compute_parameters_on_variables_update,
)
from experiment_control.compute_device_parameters.image_analysis import (
    find_how_to_analyze_images,
    find_how_to_rearrange,
)
from image_types import ImageLabel, Image
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
from sequencer.configuration import SequencerConfiguration
from sequencer.runtime import Sequencer
from units import Quantity, units, DimensionalityError
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace
from .device_context_manager import DeviceContextManager
from .device_servers import (
    create_device_servers,
    connect_to_device_servers,
    create_devices,
)
from .sequence_context import StepContext
from .user_input_loop.exec_user_input import ExecUserInput
from .user_input_loop.input_widget import RawVariableRange, EvaluatedVariableRange

if TYPE_CHECKING:
    from camera.runtime import Camera
    from aod_tweezer_arranger.runtime import AODTweezerArranger

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

WATCH_FOR_INTERRUPTION_INTERVAL = 0.1  # seconds


# This is the number of processes that can run in parallel to compile the shots.
NUMBER_WORKERS = 4

PARAMETER_QUEUE_SIZE = 10
DEVICE_PARAMETER_QUEUE_SIZE = 8
STORAGE_QUEUE_SIZE = 10


class ShotParameters(NamedTuple):
    """Holds information necessary to compile a shot."""

    shot_name: str
    shot_context: StepContext


class ShotDeviceParameters(NamedTuple):
    """Holds information necessary to execute a shot.

    Args:
        shot_name: The name of the shot.
        step_context: The context of the step that must be executed.
        change_parameters: The parameters that needs to be changed do to a variable having changed between shots, as
        computed by compute_parameters_on_variables_update. If no variable changed, this will be an empty dict.
        static_parameters: The parameters that need to be set for the shot, as computed by compute_shot_parameters. Even
        if no variable changed, this will be a non-empty dict.
    """

    shot_name: str
    step_context: StepContext
    change_parameters: dict[DeviceName, dict[DeviceParameter, Any]]
    static_parameters: dict[DeviceName, dict[DeviceParameter, Any]]


class ShotMetadata(NamedTuple):
    """Holds information necessary to store a shot.

    Args:
        shot_name: The name of the shot.
        start_time: The time at which the shot started.
        end_time: The time at which the shot ended.
        variables: The values of the variables that were used to execute the shot.
        data: The actual data that was acquired during the shot.
    """

    shot_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    variables: VariableNamespace
    data: dict[DeviceName, dict[DataLabel, Data]]


class SequenceRunnerThread(Thread):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
        must_interrupt: Event,
    ):
        super().__init__(name=f"thread_{str(sequence_path)}")
        self._session_maker = session_maker
        self._session = session_maker()
        self._save_session = session_maker()
        self._sequence = Sequence(sequence_path)
        self._devices: dict[DeviceName, RuntimeDevice] = {}

        # We watch this event while running the sequence and raise SequenceInterrupted if it becomes set.
        self._must_interrupt = must_interrupt

        self._shot_parameters_queue: asyncio.Queue[ShotParameters] = asyncio.Queue(
            maxsize=PARAMETER_QUEUE_SIZE
        )

        # This queue contains the information of the next shots to execute. Items are added when new shot parameters are
        # computed, and consumed when the shots are executed.
        self._device_parameters_queue: asyncio.Queue[
            ShotDeviceParameters
        ] = asyncio.Queue(maxsize=DEVICE_PARAMETER_QUEUE_SIZE)

        # When a shot is finished, its data is added to this queue. The data is then saved to the database.
        self._storage_queue: asyncio.Queue[ShotMetadata] = asyncio.Queue(
            maxsize=STORAGE_QUEUE_SIZE
        )

        # This stack is used to ensure that proper cleanup is done when an error occurs.
        # For now, it is only used to close the devices properly.
        self._shutdown_stack = contextlib.ExitStack()

        # This executor is used to run the computations that are done in the background. Using a ProcessPoolExecutor
        # allows to run them in parallel unlike a ThreadPoolExecutor that runs them concurrently.
        self._computation_executor = ProcessPoolExecutor()

        with self._session.activate() as session:
            self._experiment_config = session.experiment_configs[experiment_config_name]
            self._experiment_config_yaml = self._experiment_config.to_yaml()
            self._sequence_config = self._sequence.get_config(session)
            self._sequence.set_experiment_config(experiment_config_name, session)
            self._sequence.set_state(State.PREPARING, session)

        self._image_analysis_flow = {}

    def run(self):
        logger.debug(f"Image analysis flow: {self._image_analysis_flow}")
        try:
            self._run()
        except* SequenceInterruptedException:
            self.finish(State.INTERRUPTED)
            logger.info("Sequence interrupted")
        except* Exception:
            self.finish(State.CRASHED)
            logger.error("An error occurred while running the sequence", exc_info=True)
            raise
        else:
            self.finish(State.FINISHED)
            logger.info("Sequence finished")

    def _run(self):
        try:
            with self._shutdown_stack:
                asyncio.run(self.async_run())
                logger.debug("Finished async run")
            logger.debug("Closed devices")
        finally:
            self._computation_executor.shutdown(wait=False)
        logger.debug("Closed subprocesses")

    async def async_run(self):
        await self.prepare()
        await self.run_sequence()

    async def prepare(self):
        self._image_analysis_flow = find_how_to_analyze_images(
            self._sequence_config.shot_configurations["shot"]
        )

        self._image_flow, self._rearrange_flow = find_how_to_rearrange(
            self._sequence_config.shot_configurations["shot"]
        )
        logger.debug(f"{self._image_flow=}")
        logger.debug(f"{self._rearrange_flow=}")

        devices = self._create_uninitialized_devices()
        logger.debug(devices)

        for device_name, device in devices.items():
            # We initialize the devices through the stack to unsure that they are closed if an error occurs.
            self._devices[device_name] = self._shutdown_stack.enter_context(
                DeviceContextManager(device)
            )

        async with asyncio.TaskGroup() as task_group:
            for device in self._devices.values():
                task_group.create_task(asyncio.to_thread(initialize_device, device))

        with self._session.activate() as session:
            self._sequence.set_state(State.RUNNING, session)

    def _create_uninitialized_devices(self) -> dict[DeviceName, RuntimeDevice]:
        """Create the devices on their respective servers.

        The devices are created with the initial parameters specified in the experiment and sequence configs, but the
        connection to the devices is not established. The device objects are proxies to the actual devices that are
        running in other processes, possibly on other computers.
        """

        remote_device_servers = create_device_servers(
            self._experiment_config.device_servers
        )
        connect_to_device_servers(remote_device_servers)

        initialization_parameters = get_devices_initialization_parameters(
            self._experiment_config, self._sequence_config
        )
        devices = create_devices(
            initialization_parameters,
            remote_device_servers,
            self._experiment_config.mock_experiment,
        )
        return devices

    def finish(self, state: State):
        with self._session as session:
            self._sequence.set_state(state, session)

    async def run_sequence(self):
        """Run the sequence.

        This function will first run the sequence header used to populate the context with constants, then it will run
        the sequence program containing the shots.
        """

        context = StepContext[AnalogValue]()

        async with asyncio.TaskGroup() as task_group:
            watch_for_interruption = task_group.create_task(
                self.watch_for_interruption()
            )
            compile_shots = task_group.create_task(self.compile_shots())
            run_shots = task_group.create_task(self.run_shots())
            store_shots = task_group.create_task(self.store_shots())
            context = await self.run_step(self._experiment_config.header, context)
            _ = await self.run_step(self._sequence_config.program, context)
            await self._shot_parameters_queue.join()
            await self._device_parameters_queue.join()
            await self._storage_queue.join()
            compile_shots.cancel()
            run_shots.cancel()
            store_shots.cancel()
            watch_for_interruption.cancel()

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
                shot_parameters.shot_name,
                shot_parameters.shot_context,
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
    async def run_step(self, step: Step, context: StepContext) -> StepContext:
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
    async def _(
        self,
        steps: SequenceSteps,
        context: StepContext,
    ) -> StepContext:
        """Execute the steps of a SequenceSteps.

        This function executes the child steps of a SequenceSteps in order. The context is updated after each step and
        the updated context is passed to the next step.
        """

        for step in steps.children:
            context = await self.run_step(step, context)
        return context

    @run_step.register
    async def _(
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
    async def _(
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
                context = await self.run_step(step, context)
        return context

    @run_step.register
    async def _(
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
                context = await self.run_step(step, context)
        return context

    @run_step.register
    async def _(self, shot: ExecuteShot, context: StepContext) -> StepContext:
        """Compute the parameters of a shot and push them to the queue to be executed."""

        await self._shot_parameters_queue.put(
            ShotParameters(shot_name=shot.name, shot_context=context)
        )

        return context.reset_history()

    async def compute_shot_parameters(
        self, shot_name: str, context: StepContext, executor: Executor
    ) -> ShotDeviceParameters:
        with DurationTimerLog(
            logger, "Shot parameters computation", display_start=True
        ):
            # For some reason, ExperimentConfiguration cannot be pickled when using a ProcessPoolExecutor, so we pass
            # the yaml representation of the configuration instead.
            compute_change_params_task = async_run_in_executor(
                executor,
                _wrap_compute_parameters_on_variables_update,
                context.updated_variables,
                context.variables,
                self._experiment_config_yaml,
            )

            compute_static_params_task = async_run_in_executor(
                executor,
                _wrap_compute_shot_parameters,
                self._experiment_config_yaml,
                self._sequence_config.shot_configurations[shot_name],
                context.variables,
            )
            change_params = await compute_change_params_task
            shot_params = await compute_static_params_task

            return ShotDeviceParameters(
                shot_name=shot_name,
                step_context=context,
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

    async def do_shot_with_retry(
        self,
        shot_params: ShotDeviceParameters,
    ) -> ShotMetadata:
        number_of_attempts = 2  # must >= 1
        for attempt in range(number_of_attempts):
            errors: list[Exception] = []
            try:
                with DurationTimer() as timer:
                    data = await self.do_shot(
                        shot_params.change_parameters, shot_params.static_parameters
                    )
            except* CameraTimeoutError as e:
                errors.extend(e.exceptions)
                logger.warning(
                    "A camera timeout error occurred, attempting to redo the failed shot"
                )
            else:
                return ShotMetadata(
                    shot_name=shot_params.shot_name,
                    start_time=timer.start_time,
                    end_time=timer.end_time,
                    variables=shot_params.step_context.variables,
                    data=data,
                )
            logger.warning(f"Attempt {attempt+1}/{number_of_attempts} failed")
        # noinspection PyUnboundLocalVariable
        raise ExceptionGroup(
            f"Could not execute shot after {number_of_attempts} attempts", errors
        )

    async def do_shot(
        self,
        change_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]],
        device_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]],
    ) -> dict[DeviceName, Any]:
        with DurationTimerLog(logger, "Updating devices", display_start=True):
            await self.update_device_parameters(change_parameters)
            await self.update_device_parameters(device_parameters)

        with DurationTimerLog(logger, "Running shot", display_start=True):
            data = await self.run_shot()
        return data

    async def update_device_parameters(
        self, device_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]]
    ):
        if self._experiment_config.mock_experiment:
            return

        async with asyncio.TaskGroup() as update_group:
            # There is no need to shield the tasks from cancellation because they are running synchronous functions
            # in other threads and cannot be cancelled in middle of execution.
            # Some devices might be updated while others not if an exception is raised, but I don't think it is a
            # problem.
            for device_name, parameters in device_parameters.items():
                task = asyncio.to_thread(
                    update_device, self._devices[device_name], parameters
                )
                update_group.create_task(task)

    async def run_shot(self) -> dict[DeviceName, dict[DataLabel, Data]]:
        """Perform the shot.

        This is the actual shot execution that determines how to use the devices within a shot. It assumes that the
        devices have been correctly configured before.
        """

        data: dict[DeviceName, dict[DataLabel, Data]] = {}

        sequencers = self.get_sequencers_in_use()
        cameras = self.get_cameras_in_use()
        tweezer_arrangers = self.get_tweezer_arrangers_in_use()

        with DurationTimerLog(logger, "Starting devices", display_start=True):
            for tweezer_arrangers in tweezer_arrangers.values():
                tweezer_arrangers.start_sequence()
            for camera in cameras.values():
                camera.start_acquisition()
            # we need the sequencers to be correctly triggered, so we start them in their priority order
            for sequencer in sequencers.values():
                sequencer.start_sequence()

        with DurationTimerLog(logger, "Doing shot", display_start=True):
            camera_tasks = {}
            async with asyncio.TaskGroup() as run_group:
                for camera_name, camera in cameras.items():
                    camera_tasks[camera_name] = run_group.create_task(
                        self.fetch_and_analyze_images(camera_name, camera)
                    )
                for sequencer in sequencers.values():
                    run_group.create_task(wait_on_sequencer(sequencer))

        for camera_name, camera_task in camera_tasks.items():
            data |= camera_task.result()

        return data

    async def fetch_and_analyze_images(
        self, camera_name: DeviceName, camera: "Camera"
    ) -> dict[DeviceName, dict[DataLabel, Data]]:
        picture_names = camera.get_picture_names()

        result: dict[DeviceName, dict[DataLabel, Data]] = {}
        pictures = {}
        for picture_name in picture_names:
            picture = await get_picture_from_camera(camera, picture_name)
            pictures[picture_name] = picture
            logger.debug(
                f"Got picture '{picture_name}' from camera '{camera.get_name()}'"
            )
            if (camera_name, picture_name) in self._image_flow:
                for detector, imaging_config in self._image_flow[
                    (camera_name, picture_name)
                ]:
                    atoms = self._devices[detector].are_atoms_present(
                        picture, imaging_config
                    )
                    logger.debug(
                        f"Detector '{detector}' found atoms: {atoms} in picture '{picture_name}'"
                    )
                    if not detector in result:
                        result[detector] = {}
                    result[detector][picture_name] = atoms
                    if (detector, picture_name) in self._rearrange_flow:
                        tweezer_arranger, step = self._rearrange_flow[
                            (detector, picture_name)
                        ]
                        self._devices[tweezer_arranger].prepare_rearrangement(
                            step=step, atom_present=atoms
                        )
                        logger.debug(
                            f"Tweezer arranger '{tweezer_arranger}' arranged tweezers in picture '{picture_name}'"
                        )
        camera.stop_acquisition()

        result[camera_name] = pictures
        return result

    async def store_shot(
        self,
        shot_data: ShotMetadata,
    ) -> Shot:
        with DurationTimerLog(logger, "Saving shot", display_start=True):
            return await asyncio.to_thread(self.save_shot, shot_data)

    def save_shot(
        self,
        shot_data: ShotMetadata,
    ) -> Shot:
        with self._save_session as session:
            params = {
                name: value
                for name, value in shot_data.variables.to_flat_dict().items()
            }
            return self._sequence.create_shot(
                name=shot_data.shot_name,
                start_time=shot_data.start_time,
                end_time=shot_data.end_time,
                parameters=params,
                measures=shot_data.data,
                experiment_session=session,
            )

    def get_sequencers_in_use(self) -> dict[DeviceName, Sequencer]:
        """Return the sequencer devices used in the experiment.

        The sequencers are sorted by trigger priority, with the highest priority first.
        """

        # Here we can't test the type of the runtime device itself because it is actually a proxy and not an instance of
        # the actual device class, that's why we need to test the type of the configuration instead.
        sequencers: dict[DeviceName, Sequencer] = {
            device_name: device
            for device_name, device in self._devices.items()
            if isinstance(
                self._experiment_config.get_device_config(device_name),
                SequencerConfiguration,
            )
        }
        sorted_by_trigger_priority = sorted(
            sequencers.items(), key=lambda x: x[1].get_trigger_priority(), reverse=True
        )
        return dict(sorted_by_trigger_priority)

    def get_cameras_in_use(self) -> dict[DeviceName, "Camera"]:
        return {
            device_name: device  # type: ignore
            for device_name, device in self._devices.items()
            if isinstance(
                self._experiment_config.get_device_config(device_name),
                CameraConfiguration,
            )
        }

    def get_tweezer_arrangers_in_use(self) -> dict[DeviceName, "AODTweezerArranger"]:
        return {
            device_name: device  # type: ignore
            for device_name, device in self._devices.items()
            if isinstance(
                self._experiment_config.get_device_config(device_name),
                AODTweezerArrangerConfiguration,
            )
        }


def initialize_device(device: RuntimeDevice):
    """Initialize a device.

    The goal of this function is to provide a more informative error message when a device fails to initialize.
    """
    try:
        device.initialize()
        logger.info(f"Device '{device.get_name()}' started.")
    except Exception as error:
        raise RuntimeError(f"Could not start device '{device.get_name()}'") from error


def update_device(device: RuntimeDevice, parameters: Mapping[DeviceParameter, Any]):
    try:
        if parameters:
            device.update_parameters(**parameters)
    except Exception as error:
        raise RuntimeError(f"Failed to update device {device.get_name()}") from error


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


async def wait_on_sequencer(sequencer: Sequencer):
    """Wait for a sequencer to finish."""

    while not sequencer.has_sequence_finished():
        await asyncio.sleep(10e-3)


async def get_picture_from_camera(camera: "Camera", picture_name: ImageLabel) -> Image:
    while (image := camera.get_picture(picture_name)) is None:
        await asyncio.sleep(1e-3)
    return image


# This exception is used to interrupt the sequence and inherit from BaseException to prevent it from being caught
# accidentally.
class SequenceInterruptedException(BaseException):
    pass
