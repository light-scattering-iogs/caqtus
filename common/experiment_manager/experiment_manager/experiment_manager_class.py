import datetime
import io
import logging
import os
from concurrent.futures import Executor, ThreadPoolExecutor
from copy import copy
from enum import Enum, auto
from functools import singledispatchmethod, cached_property
from pathlib import Path
from threading import Thread
from typing import Any, TypedDict, Iterable

import h5py
import numpy
import yaml

from camera import CCamera
from experiment_config import (
    ExperimentConfig,
    ChannelSpecialPurpose,
    SpincoreSequencerConfiguration,
    NI6738SequencerConfiguration,
    CameraConfiguration,
)
from ni6738_analog_card import NI6738AnalogCard
from remote_device_client import RemoteDeviceClientManager
from sequence import (
    SequenceStats,
    SequenceState,
    Step,
    SequenceConfig,
    SequenceSteps,
    VariableDeclaration,
)
from sequence.sequence_config import ArangeLoop, LinspaceLoop, ExecuteShot
from settings_model import YAMLSerializable
from shot import (
    ShotConfiguration,
    evaluate_step_durations,
    evaluate_analog_local_times,
    evaluate_analog_values,
    CameraLane,
)
from spincore_sequencer import Instruction, Continue, Loop, SpincorePulseBlaster
from spincore_sequencer.instructions import Stop
from units import units, Quantity, ureg

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentState(Enum):
    IDLE = auto()
    RUNNING = auto()
    WAITING_TO_INTERRUPT = auto()


class CameraInstructions(TypedDict):
    timeout: float
    exposures: list[float]
    triggers: list[bool]


class SequenceContext:
    def __init__(self, variables: dict[str]):
        self.variables = variables
        self.delayed_executor: Executor = ThreadPoolExecutor()
        self.shot_numbers: dict[str, int] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delayed_executor.shutdown(wait=True)


def compile_camera_instructions(
    step_durations: list[float], shot: ShotConfiguration
) -> dict[str, CameraInstructions]:
    result = {}
    camera_lanes = shot.get_lanes(CameraLane)
    timeout = sum(step_durations)
    for camera_name, camera_lane in camera_lanes.items():
        triggers = [False] * len(step_durations)
        exposures = []
        for _, start, stop in camera_lane.get_picture_spans():
            triggers[start:stop] = [True] * (stop - start)
            exposures.append(sum(step_durations[start:stop]))
        instructions: CameraInstructions = {
            "timeout": timeout,
            "triggers": triggers,
            "exposures": exposures,
        }
        result[camera_name] = instructions
    return result


def save_shot(
    file_path: Path,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    variables: dict[str, Quantity],
    data: dict[str],
):
    data_buffer = io.BytesIO()
    with h5py.File(data_buffer, "w") as file:
        file.attrs["start_time"] = start_time.strftime("%Y-%m-%d-%Hh%Mm%Ss%fus")
        file.attrs["end_time"] = end_time.strftime("%Y-%m-%d-%Hh%Mm%Ss%fus")
        file.create_dataset("variables/names", data=list(variables.keys()))
        file.create_dataset(
            "variables/units",
            data=[str(quantity.units) for quantity in variables.values()],
        )
        file.create_dataset(
            "variables/magnitudes",
            data=[float(quantity.magnitude) for quantity in variables.values()],
        )
        for device, device_data in data.items():
            if isinstance(device_data, dict):
                for key, value in device_data.items():
                    file.create_dataset(f"data/{device}/{key}", data=value)

    if file_path.is_file():
        raise RuntimeError(f"{file_path} already exists and won't be overwritten.")
    with open(file_path, "wb") as file:
        # noinspection PyTypeChecker
        file.write(data_buffer.getbuffer())


class SequenceRunnerThread(Thread):
    def __init__(
        self, experiment_config: str, sequence_path: Path, parent: "ExperimentManager"
    ):
        super().__init__(name=f"thread_{str(sequence_path)}")
        self.experiment_config: ExperimentConfig = yaml.load(
            experiment_config, Loader=YAMLSerializable.get_loader()
        )
        self.sequence_path = self.experiment_config.data_path / sequence_path
        self.parent = parent
        self.stats = SequenceStats(state=SequenceState.RUNNING)
        self.shot_numbers = {"shot": 0}
        with open(self.sequence_path / "sequence_config.yaml", "r") as file:
            self.sequence_config: SequenceConfig = yaml.load(
                file, Loader=YAMLSerializable.get_loader()
            )

        self.spincore = SpincorePulseBlaster(
            **self.spincore_config.get_device_init_args()
        )

        self.ni6738 = NI6738AnalogCard(**self.ni6738_config.get_device_init_args())
        self.cameras: dict[str, CCamera] = {}

        self.remote_device_managers: dict[str, RemoteDeviceClientManager] = {}
        for server_name, server_config in self.experiment_config.device_servers.items():
            ipaddress = server_config.address
            port = server_config.port
            address = (ipaddress, port)
            authkey = bytes(server_config.authkey.get_secret_value(), encoding="utf-8")
            self.remote_device_managers[server_name] = RemoteDeviceClientManager(
                address=address, authkey=authkey
            )

        self.shutdown_actions = []

    def run(self):
        # noinspection PyBroadException
        try:
            self.prepare()
            self.run_sequence()
            self.finish()
        except Exception:
            self.record_exception()
            logger.error("An error occurred while running the sequence", exc_info=True)
        finally:
            self.shutdown()

    def prepare(self):
        self.stats.start_time = datetime.datetime.now()
        YAMLSerializable.dump(self.stats, self.sequence_path / "sequence_state.yaml")
        YAMLSerializable.dump(
            self.experiment_config, self.sequence_path / "experiment_config.yaml"
        )
        for server_name, server in self.remote_device_managers.items():
            logger.info(f"Connecting to device server {server_name}...")
            server.connect()
            logger.info(f"Connection established to {server_name}")

        self.ni6738.start()
        self.shutdown_actions.append(self.ni6738.shutdown)
        self.spincore.start()
        self.shutdown_actions.append(self.spincore.shutdown)

        camera_configs = self.experiment_config.get_device_configs(CameraConfiguration)
        camera_lanes = self.sequence_config.shot_configurations["shot"].get_lanes(
            CameraLane
        )
        for camera_name, camera_lane in camera_lanes.items():
            if camera_name not in camera_configs:
                raise RuntimeError(
                    f"There is no camera configuration associated to {camera_name}"
                )
            camera_config = camera_configs[camera_name]
            server = self.remote_device_managers[camera_config.remote_server]
            init_args = camera_config.get_device_init_args()
            init_args["picture_names"] = camera_lane.get_picture_names()
            init_args["exposures"] = [0] * len(init_args["picture_names"])
            self.cameras[camera_name] = getattr(
                server, camera_config.get_device_type()
            )(**init_args)
            self.cameras[camera_name].start()
            self.shutdown_actions.append(self.cameras[camera_name].shutdown)

    def finish(self):
        self.stats.stop_time = datetime.datetime.now()
        if self.is_waiting_to_interrupt():
            self.stats.state = SequenceState.INTERRUPTED
        else:
            self.stats.state = SequenceState.FINISHED
        YAMLSerializable.dump(self.stats, self.sequence_path / "sequence_state.yaml")

    def record_exception(self):
        self.stats.stop_time = datetime.datetime.now()
        self.stats.state = SequenceState.CRASHED
        YAMLSerializable.dump(self.stats, self.sequence_path / "sequence_state.yaml")

    def shutdown(self):
        for action in self.shutdown_actions:
            # noinspection PyBroadException
            try:
                action()
            except Exception:
                logger.error("An error occurred when shutting down", exc_info=True)
        logger.info("Sequence finished")
        self.parent.set_state(ExperimentState.IDLE)

    def run_sequence(self):
        """Walk through the sequence program and execute each step sequentially"""
        with SequenceContext(variables={}) as context:
            self.run_step(self.experiment_config.header, context)
            self.run_step(self.sequence_config.program, context)

    @singledispatchmethod
    def run_step(self, step: Step, context: SequenceContext):
        """Execute a given step of the sequence

        This function should be implemented for each Step type that can be run on the experiment. It should also return
        as soon as possible if the sequence needs to be interrupted.

        Args:
            step: the step of the sequence currently executed
            context: a mutable object that holds information about the sequence being run, such as the values of the
            variables. Step that update variables should reflect this by modifying the context.

        Returns:
            updated context after the step was executed
        """

        raise NotImplementedError(f"run_step is not implemented for {type(step)}")

    @run_step.register
    def _(self, steps: SequenceSteps, context: SequenceContext):
        """Execute each child step sequentially"""

        for step in steps.children:
            if self.is_waiting_to_interrupt():
                return
            else:
                self.run_step(step, context)

    @run_step.register
    def _(self, declaration: VariableDeclaration, context: SequenceContext):
        """Add or update a variable declaration in the context"""

        context.variables[declaration.name] = Quantity(
            declaration.expression.evaluate(context.variables | units)
        )

    @run_step.register
    def _(self, arange_loop: ArangeLoop, context: SequenceContext):
        """Loop over a variable in a numpy arange like loop and execute children steps at each repetition"""
        start = Quantity(arange_loop.start.evaluate(context.variables | units))
        stop = Quantity(arange_loop.stop.evaluate(context.variables | units))
        step = Quantity(arange_loop.step.evaluate(context.variables | units))

        unit = start.units

        for value in numpy.arange(
            start.to(unit).magnitude, stop.to(unit).magnitude, step.to(unit).magnitude
        ):
            context.variables[arange_loop.name] = value * unit
            for step in arange_loop.children:
                if self.is_waiting_to_interrupt():
                    return
                else:
                    self.run_step(step, context)

    @run_step.register
    def _(self, linspace_loop: LinspaceLoop, context: SequenceContext):
        """Loop over a variable in a numpy linspace like loop and execute children steps at each repetition"""
        start = Quantity(linspace_loop.start.evaluate(context.variables | units))
        stop = Quantity(linspace_loop.stop.evaluate(context.variables | units))
        num = int(linspace_loop.num)

        unit = start.units

        for value in numpy.linspace(
            start.to(unit).magnitude, stop.to(unit).magnitude, num
        ):
            context.variables[linspace_loop.name] = value * unit
            for step in linspace_loop.children:
                if self.is_waiting_to_interrupt():
                    return
                else:
                    self.run_step(step, context)

    @run_step.register
    def _(self, shot: ExecuteShot, context: SequenceContext):
        """Execute a shot on the experiment"""

        t0 = datetime.datetime.now()
        try:
            data = self.do_shot(
                self.sequence_config.shot_configurations[shot.name], context.variables
            )
        except TimeoutError:
            logger.warning(f"Camera timeout error, retrying once")
            for camera in self.cameras.values():
                camera.reset_acquisition()
            data = self.do_shot(
                self.sequence_config.shot_configurations[shot.name], context.variables
            )

        old_shot_number = context.shot_numbers.get(shot.name, 0)
        context.shot_numbers[shot.name] = old_shot_number + 1

        shot_file_path = (
            self.sequence_path / f"{shot.name}_{context.shot_numbers[shot.name]}.hdf5"
        )

        t1 = datetime.datetime.now()
        logger.info(f"shot executed in {(t1 - t0)}")
        context.delayed_executor.submit(
            save_shot, shot_file_path, t0, t1, copy(context.variables), data
        )

    def do_shot(self, shot: ShotConfiguration, context: dict[str]) -> dict[str, Any]:
        step_durations = evaluate_step_durations(shot, context)
        self.check_durations(shot, step_durations)
        camera_instructions = compile_camera_instructions(step_durations, shot)
        for camera, instructions in camera_instructions.items():
            self.cameras[camera].apply_rt_variables(
                timeout=instructions["timeout"], exposures=instructions["exposures"]
            )
        camera_triggers = {
            camera_name: instructions["triggers"]
            for camera_name, instructions in camera_instructions.items()
        }
        spincore_instructions, analog_values = self.compile_sequencer_instructions(
            step_durations, shot, context, camera_triggers
        )

        analog_voltages = self.generate_analog_voltages(analog_values)
        self.ni6738.apply_rt_variables(values=analog_voltages)
        self.ni6738.run()

        camera_threads = [
            Thread(target=camera.acquire_all_pictures)
            for camera in self.cameras.values()
        ]
        logger.debug(f"camera threads: {camera_threads}")
        for thread in camera_threads:
            thread.start()
        self.spincore.apply_rt_variables(instructions=spincore_instructions)
        self.spincore.run()
        for thread in camera_threads:
            thread.join()
        data = {}
        for name, camera in self.cameras.items():
            data[name] = camera.read_all_pictures()
        return data

    def is_waiting_to_interrupt(self) -> bool:
        return self.parent.get_state() == ExperimentState.WAITING_TO_INTERRUPT

    def compile_sequencer_instructions(
        self,
        step_durations: list[float],
        shot: ShotConfiguration,
        context: dict[str],
        camera_triggers: dict[str, list[bool]],
    ) -> tuple[list[Instruction], dict[str, Quantity]]:
        """Return the spincore instructions and the analog values for the ni6738"""

        analog_times = evaluate_analog_local_times(
            shot,
            step_durations,
            self.ni6738_config.time_step,
            self.spincore.time_step,
        )

        instructions = self.generate_digital_instructions(
            shot, step_durations, analog_times, camera_triggers
        )

        analog_values = evaluate_analog_values(shot, analog_times, context)
        return instructions, analog_values

    def check_durations(self, shot: ShotConfiguration, durations: list[float]):
        for step_name, duration in zip(shot.step_names, durations):
            if duration < self.spincore.time_step:
                raise ValueError(
                    f"Duration of step '{step_name}' ({(duration * ureg.s).to('ns')})"
                    " is too short"
                )

    def generate_digital_instructions(
        self,
        shot: ShotConfiguration,
        step_durations: list[float],
        analog_times: list[numpy.ndarray],
        camera_triggers: dict[str, list[bool]],
    ) -> list[Instruction]:
        analog_time_step = self.ni6738_config.time_step
        instructions = []
        # noinspection PyTypeChecker
        analog_clock_channel = self.spincore_config.get_channel_index(
            ChannelSpecialPurpose(purpose="NI6738 analog sequencer")
        )
        camera_channels = self.get_camera_channels(camera_triggers.keys())
        values = [False] * self.spincore_config.number_channels
        for step in range(len(step_durations)):
            values = [False] * self.spincore_config.number_channels
            for camera, triggers in camera_triggers.items():
                values[camera_channels[camera]] = triggers[step]
            for lane in shot.digital_lanes:
                channel = self.spincore_config.get_channel_index(lane.name)
                values[channel] = lane.get_effective_value(step)
            if len(analog_times[step]) > 0:
                duration = analog_times[step][0]
            else:
                duration = step_durations[step]
            instructions.append(Continue(values=values, duration=duration))
            if len(analog_times[step]) > 0:
                (low_values := copy(values))[analog_clock_channel] = False
                (high_values := copy(low_values))[analog_clock_channel] = True
                instructions.append(
                    Loop(
                        repetitions=len(analog_times[step]),
                        start_values=high_values,
                        start_duration=analog_time_step / 2,
                        end_values=low_values,
                        end_duration=analog_time_step / 2,
                    )
                )
                instructions.append(
                    Continue(
                        values=low_values,
                        duration=step_durations[step]
                        - (analog_times[step][-1] + analog_time_step),
                    )
                )
        instructions.append(Stop(values=values))
        return instructions

    def get_camera_channels(self, camera_names: Iterable[str]) -> dict[str, int]:
        return {
            name: self.spincore_config.get_channel_index(
                ChannelSpecialPurpose(purpose=name)
            )
            for name in camera_names
        }

    def generate_analog_voltages(self, analog_values: dict[str, Quantity]):
        data_length = 0
        for array in analog_values.values():
            data_length = len(array)
            break
        data = numpy.zeros(
            (NI6738AnalogCard.channel_number, data_length), dtype=numpy.float64
        )

        for name, values in analog_values.items():
            voltages = (
                self.ni6738_config.convert_to_output_units(name, values)
                .to("V")
                .magnitude
            )
            channel_number = self.ni6738_config.get_channel_index(name)
            data[channel_number] = voltages
        return data

    @cached_property
    def spincore_config(self) -> SpincoreSequencerConfiguration:
        return self.experiment_config.spincore_config

    @cached_property
    def ni6738_config(self) -> NI6738SequencerConfiguration:
        return self.experiment_config.ni6738_config


class ExperimentManager:
    def __init__(self):
        logger.info(f"Started experiment manager in process {os.getpid()}")
        self._state: ExperimentState = ExperimentState.IDLE
        self._sequence_runner_thread = None

    def get_state(self) -> ExperimentState:
        return self._state

    def set_state(self, value):
        self._state = value

    def is_running(self) -> bool:
        return self._state != ExperimentState.IDLE

    def _sequence_finished(self):
        self._state = ExperimentState.IDLE

    def start_sequence(self, experiment_config: str, sequence_path: Path) -> bool:
        """Attempts to start the sequence

        Return True if the sequence was started, False if not.
        """
        if self._state == ExperimentState.IDLE:
            self._sequence_runner_thread = SequenceRunnerThread(
                experiment_config, sequence_path, self
            )
            self._sequence_runner_thread.start()
            self._state = ExperimentState.RUNNING
            return True
        else:
            return False

    def interrupt_sequence(self) -> bool:
        if self._state == ExperimentState.RUNNING:
            self._state = ExperimentState.WAITING_TO_INTERRUPT
            logger.info("Sequence waiting to interrupt")
            return True
        return False
