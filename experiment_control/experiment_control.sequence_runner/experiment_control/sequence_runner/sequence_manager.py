import asyncio
import logging
import time
from asyncio import PriorityQueue, Event
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from contextlib import AbstractContextManager, ExitStack
from datetime import datetime
from typing import Self, Any, Optional, Mapping

from attr import frozen, field

from camera.runtime import CameraTimeoutError, Camera
from data_types import DataLabel, Data
from device.configuration import DeviceParameter
from device.name import DeviceName
from device.runtime import RuntimeDevice
from duration_timer import DurationTimerLog, DurationTimer
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker
from experiment_control.compute_device_parameters import (
    get_devices_initialization_parameters,
    compute_parameters_on_variables_update,
    compute_shot_parameters,
)
from experiment_control.compute_device_parameters.image_analysis import (
    find_how_to_analyze_images,
    find_how_to_rearrange,
)
from image_types import ImageLabel, Image
from sequence.configuration import SequenceConfig
from sequence.runtime import SequencePath, Sequence, State, Shot
from sequencer.runtime import Sequencer
from tweezer_arranger.runtime import RearrangementFailedError
from variable.namespace import VariableNamespace
from .device_servers import (
    create_device_servers,
    connect_to_device_servers,
    create_devices,
)
from .devices_handler import DevicesHandler
from .sequence_context import StepContext
from .task_group import TaskGroup

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@frozen(order=True)
class ShotParameters:
    """Holds information necessary to compile a shot."""

    name: str
    index: int
    context: StepContext = field(eq=False)


@frozen(order=True)
class ShotDeviceParameters:
    """Holds information necessary to execute a shot.

    Args:
        name: The name of the shot.
        index: The index of the shot.
        context: The context of the step that must be executed.
        change_parameters: The parameters that needs to be changed do to a variable having changed between shots, as
        computed by compute_parameters_on_variables_update. If no variable changed, this will be an empty dict.
        static_parameters: The parameters that need to be set for the shot, as computed by compute_shot_parameters. Even
        if no variable changed, this will be a non-empty dict.
    """

    name: str
    index: int
    context: StepContext = field(eq=False)
    change_parameters: dict[DeviceName, dict[DeviceParameter, Any]] = field(eq=False)
    static_parameters: dict[DeviceName, dict[DeviceParameter, Any]] = field(eq=False)


@frozen(order=True)
class ShotMetadata:
    """Holds information necessary to store a shot.

    Args:
        name: The name of the shot.
        start_time: The time at which the shot started.
        end_time: The time at which the shot ended.
        variables: The values of the variables that were used to execute the shot.
        data: The actual data that was acquired during the shot.
    """

    name: str
    index: int
    start_time: datetime = field(eq=False)
    end_time: datetime = field(eq=False)
    variables: VariableNamespace = field(eq=False)
    data: dict[DeviceName, dict[DataLabel, Data]] = field(eq=False)


class SequenceManager(AbstractContextManager):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
        max_schedulable_shots: Optional[int] = 10,
    ) -> None:
        self._experiment_config_name = experiment_config_name
        self._experiment_config: ExperimentConfig
        self._sequence = Sequence(sequence_path)
        self._sequence_config: SequenceConfig
        self._session_maker = session_maker

        self._exit_stack = ExitStack()
        self._thread_pool = ThreadPoolExecutor()
        self._process_pool = ProcessPoolExecutor()
        self._asked_to_interrupt = False
        self._stop_background_tasks = Event()

        self._runner = asyncio.Runner()

        self._device_manager: DevicesHandler

        if max_schedulable_shots is None:
            max_schedulable_shots = 0
        self._shot_parameters_queue = PriorityQueue[ShotParameters](
            max_schedulable_shots
        )
        self._device_shot_parameters_queue = PriorityQueue[ShotDeviceParameters](
            max_schedulable_shots
        )
        self._data_queue = PriorityQueue[ShotMetadata]()
        self._current_shot = 0
        self._sequence_future: Future

        self._background_tasks = set()

    @property
    def experiment_config(self) -> ExperimentConfig:
        return self._experiment_config

    @property
    def sequence_config(self) -> SequenceConfig:
        return self._sequence_config

    def schedule_shot(self, shot_name: str, shot_context: StepContext) -> None:
        if self._sequence_future.done():
            if self._sequence_future.exception() is not None:
                raise RuntimeError(
                    "Can't schedule new shots because an error occurred while running the sequence"
                ) from self._sequence_future.exception()
            else:
                raise RuntimeError(
                    "Can't schedule new shots because the sequence has finished running"
                )
        shot_params = ShotParameters(
            name=shot_name, index=self._current_shot, context=shot_context
        )
        asyncio.run_coroutine_threadsafe(
            self._push_shot(shot_params),
            self._runner.get_loop(),
        ).result()
        self._current_shot += 1

    async def _push_shot(self, shot_params: ShotParameters) -> None:
        await self._shot_parameters_queue.put(shot_params)

    def __enter__(self) -> Self:
        with self._session_maker() as session:
            self._sequence.set_experiment_config(self._experiment_config_name, session)
            self._sequence.set_state(State.PREPARING, session)
        try:
            self._prepare()
            self._set_sequence_state(State.RUNNING)
            self._start_sequence()
        except Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        return self

    def _prepare(self) -> None:
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._thread_pool)
        self._exit_stack.enter_context(self._process_pool)

        with self._session_maker() as session:
            self._experiment_config = session.experiment_configs[
                self._experiment_config_name
            ]
            self._sequence_config = self._sequence.get_config(session)

        devices = self._create_uninitialized_devices()
        self._device_manager = DevicesHandler(devices, self._experiment_config)
        self._exit_stack.enter_context(self._device_manager)

        self._image_analysis_flow = find_how_to_analyze_images(
            self._sequence_config.shot_configurations["shot"]
        )

        self._image_flow, self._rearrange_flow = find_how_to_rearrange(
            self._sequence_config.shot_configurations["shot"]
        )
        logger.debug(f"{self._image_flow=}")
        logger.debug(f"{self._rearrange_flow=}")

        self._runner = asyncio.Runner()

    def _start_sequence(self) -> None:
        def fun():
            self._exit_stack.enter_context(self._runner)
            self._runner.run(self._run_sequence())
        self._sequence_future = self._thread_pool.submit(fun)

    async def _run_sequence(self) -> None:
        async with asyncio.TaskGroup() as g:
            self._background_tasks.add(g.create_task(self._consume_shot_parameters()))
            self._background_tasks.add(
                g.create_task(self._consume_device_shot_parameters())
            )
            self._background_tasks.add(g.create_task(self._consume_shot_data()))

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

    async def _consume_shot_parameters(self) -> None:
        while True:
            shot_parameters = await self._shot_parameters_queue.get()
            with DurationTimerLog(logger, "Computing shot parameters"):
                devices_shot_parameters = await asyncio.to_thread(
                    self.compute_shot_parameters, shot_parameters
                )
                await self._device_shot_parameters_queue.put(devices_shot_parameters)
                self._shot_parameters_queue.task_done()

    def compute_shot_parameters(
        self, shot_parameters: ShotParameters
    ) -> ShotDeviceParameters:
        change_params = compute_parameters_on_variables_update(
            shot_parameters.context.updated_variables,
            shot_parameters.context.variables,
            self.experiment_config,
        )
        shot_params = compute_shot_parameters(
            self.experiment_config,
            self._sequence_config.shot_configurations[shot_parameters.name],
            shot_parameters.context.variables,
        )

        return ShotDeviceParameters(
            name=shot_parameters.name,
            context=shot_parameters.context,
            index=shot_parameters.index,
            change_parameters=change_params,
            static_parameters=shot_params,
        )

    async def _consume_device_shot_parameters(self) -> None:
        while True:
            device_parameters = await self._device_shot_parameters_queue.get()
            shot_data = await self.do_shot_with_retry(device_parameters)
            await self._data_queue.put(shot_data)
            self._device_shot_parameters_queue.task_done()

    async def stop_background_tasks(self, wait: bool = True):
        if wait:
            await asyncio.gather(
                self._shot_parameters_queue.join(),
                self._device_shot_parameters_queue.join(),
                self._data_queue.join(),
                return_exceptions=True,
            )
        for task in self._background_tasks:
            task.cancel()

    async def do_shot_with_retry(
        self,
        shot_params: ShotDeviceParameters,
    ) -> ShotMetadata:
        number_of_attempts = 3  # must >= 1
        for attempt in range(number_of_attempts):
            errors: list[Exception] = []
            try:
                with DurationTimer() as timer:
                    data = await asyncio.to_thread(
                        self.do_shot,
                        shot_params.change_parameters,
                        shot_params.static_parameters,
                    )
            except* CameraTimeoutError as e:
                errors.extend(e.exceptions)
                logger.warning(
                    "A camera timeout error occurred, attempting to redo the failed shot"
                )
            except* RearrangementFailedError as e:
                errors.extend(e.exceptions)
                logger.warning("Rearrangement failed, attempting to redo the shot")
            else:
                return ShotMetadata(
                    name=shot_params.name,
                    index=shot_params.index,
                    start_time=timer.start_time,
                    end_time=timer.end_time,
                    variables=shot_params.context.variables,
                    data=data,
                )
            logger.warning(f"Attempt {attempt+1}/{number_of_attempts} failed")
        # noinspection PyUnboundLocalVariable
        raise ExceptionGroup(
            f"Could not execute shot after {number_of_attempts} attempts", errors
        )

    def do_shot(
        self,
        change_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]],
        device_parameters: Mapping[DeviceName, dict[DeviceParameter, Any]],
    ) -> dict[DeviceName, Any]:
        with DurationTimerLog(logger, "Updating devices", display_start=True):
            self._device_manager.update_device_parameters(change_parameters)
            self._device_manager.update_device_parameters(device_parameters)

        with DurationTimerLog(logger, "Running shot", display_start=True):
            data = self.run_shot()
        return data

    def run_shot(self) -> dict[DeviceName, dict[DataLabel, Data]]:
        """Perform the shot.

        This is the actual shot execution that determines how to use the devices within a shot. It assumes that the
        devices have been correctly configured before.
        """

        data: dict[DeviceName, dict[DataLabel, Data]] = {}

        with DurationTimerLog(logger, "Starting devices", display_start=True):
            self._device_manager.start_shot()

        with DurationTimerLog(logger, "Doing shot", display_start=True):
            camera_tasks = {}
            with ThreadPoolExecutor() as thread_pool, TaskGroup(thread_pool) as g:
                for camera_name, camera in self._device_manager.cameras.items():
                    camera_tasks[camera_name] = g.add_task(
                        self.fetch_and_analyze_images, camera_name, camera
                    )
                for sequencer in self._device_manager.sequencers.values():
                    g.add_task(wait_on_sequencer, sequencer)

        for camera_name, camera_task in camera_tasks.items():
            data |= camera_task.result()

        return data

    def fetch_and_analyze_images(
        self, camera_name: DeviceName, camera: "Camera"
    ) -> dict[DeviceName, dict[DataLabel, Data]]:
        picture_names = camera.get_picture_names()

        result: dict[DeviceName, dict[DataLabel, Data]] = {}
        pictures = {}
        for picture_name in picture_names:
            with DurationTimerLog(
                logger, f"Fetching picture '{picture_name}'", display_start=True
            ):
                picture = get_picture_from_camera(camera, picture_name)
            pictures[picture_name] = picture
            logger.debug(
                f"Got picture '{picture_name}' from camera '{camera.get_name()}'"
            )
            if (camera_name, picture_name) in self._image_flow:
                for detector, imaging_config in self._image_flow[
                    (camera_name, picture_name)
                ]:
                    atoms = self._device_manager._devices[detector].are_atoms_present(
                        picture, imaging_config
                    )
                    logger.debug(
                        f"Detector '{detector}' found atoms: {atoms} in picture '{picture_name}'"
                    )
                    if detector not in result:
                        result[detector] = {}
                    result[detector][picture_name] = atoms
                    if (detector, picture_name) in self._rearrange_flow:
                        tweezer_arranger, step = self._rearrange_flow[
                            (detector, picture_name)
                        ]
                        with DurationTimerLog(
                            logger, "Preparing rearrangement", display_start=True
                        ):
                            self._device_manager.tweezer_arrangers[
                                tweezer_arranger
                            ].prepare_rearrangement(step=step, atom_present=atoms)
        camera.stop_acquisition()
        logger.debug(f"Stopped acquisition of camera '{camera.get_name()}'")

        result[camera_name] = pictures
        return result

    async def _consume_shot_data(self) -> None:
        while True:
            shot_data = await self._data_queue.get()
            await asyncio.to_thread(
                save_shot, self._sequence, shot_data, self._session_maker
            )
            self._data_queue.task_done()

    def __exit__(self, exc_type, exc_value, traceback):
        error_occurred = exc_value is not None
        try:
            if error_occurred:
                self._sequence_future.cancel()
            else:
                asyncio.run_coroutine_threadsafe(
                    self.stop_background_tasks(wait=True), asyncio.get_running_loop()
                ).result()
                self._sequence_future.result()
        except Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        else:
            if error_occurred:
                if isinstance(exc_value, SequenceInterruptedError):
                    self._set_sequence_state(State.INTERRUPTED)
                    return True
                else:
                    self._set_sequence_state(State.CRASHED)
                    return False
            elif self.asked_to_interrupt():
                self._set_sequence_state(State.INTERRUPTED)
            else:
                self._set_sequence_state(State.FINISHED)
        finally:
            self._exit_stack.__exit__(exc_type, exc_value, traceback)

    def interrupt_sequence(self) -> None:
        self._asked_to_interrupt = True
        self._stop_background_tasks.set()

    def asked_to_interrupt(self) -> bool:
        return self._asked_to_interrupt

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            self._sequence.set_state(state, session)


class SequenceInterruptedError(RuntimeError):
    pass


def wait_on_sequencer(sequencer: Sequencer):
    """Wait for a sequencer to finish."""

    while not sequencer.has_sequence_finished():
        time.sleep(10e-3)


def get_picture_from_camera(camera: "Camera", picture_name: ImageLabel) -> Image:
    while (image := camera.get_picture(picture_name)) is None:
        time.sleep(1e-3)
    return image


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
