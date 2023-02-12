import datetime
import io
import logging
import pprint
import typing
from concurrent.futures import ThreadPoolExecutor, Future
from copy import deepcopy
from functools import singledispatchmethod
from pathlib import Path
from threading import Thread, Event
from typing import Any

import h5py
import numpy

from camera.configuration import CameraConfiguration
from camera.runtime import CameraTimeoutError
from device import RuntimeDevice
from experiment_config import (
    ExperimentConfig,
    SpincoreSequencerConfiguration,
    DeviceServerConfiguration,
)
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from remote_device_client import RemoteDeviceClientManager
from sequence.configuration import (
    ShotConfiguration,
    Step,
    SequenceSteps,
    ArangeLoop,
    LinspaceLoop,
    VariableDeclaration,
    ExecuteShot,
)
from units import Quantity, units
from variable import VariableNamespace
from .compute_shot_parameters import compute_shot_parameters
from .initialize_devices import get_devices_initialization_parameters
from .sequence_context import SequenceContext

if typing.TYPE_CHECKING:
    from ni6738_analog_card.runtime import NI6738AnalogCard
    from camera.runtime import CCamera
    from spincore_sequencer.runtime import SpincorePulseBlaster

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SequenceRunnerThread(Thread):
    def __init__(
        self, experiment_config: str, sequence_path: Path, waiting_to_interrupt: Event
    ):
        super().__init__(name=f"thread_{str(sequence_path)}")
        self.experiment_config = ExperimentConfig.from_yaml(experiment_config)
        self.sequence = Sequence(
            self.experiment_config.data_path / sequence_path, read_only=False
        )
        self.sequence_config = self.sequence.config
        self.stats = self.sequence.get_stats()
        self.stats.number_completed_shots = 0
        self.stats.state = SequenceState.PREPARING
        self.sequence.set_stats(self.stats)

        self._waiting_to_interrupt = waiting_to_interrupt

        self.remote_device_managers: dict[
            str, RemoteDeviceClientManager
        ] = create_remote_device_managers(self.experiment_config.device_servers)

        self.devices: dict[str, RuntimeDevice] = {}

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
        self.sequence.create_shot_folder()
        self.experiment_config.save_yaml(self.sequence.experiment_config_path)
        self.connect_to_device_servers()

        self.devices = self.create_devices()
        self.start_devices()

        self.stats.state = SequenceState.RUNNING
        self.stats.start_time = datetime.datetime.now()
        self.sequence.set_stats(self.stats)

    def connect_to_device_servers(self):
        """Start the connection to the device servers"""

        for server_name, server in self.remote_device_managers.items():
            logger.info(f"Connecting to device server {server_name}...")
            server.connect()
            logger.info(f"Connection established to {server_name}")

    def create_devices(self) -> dict[str, RuntimeDevice]:
        """Instantiate the devices on their respective remote server"""

        devices = {}
        for name, parameters in get_devices_initialization_parameters(
            self.experiment_config, self.sequence_config
        ).items():
            server = self.remote_device_managers[parameters["server"]]
            devices[name] = getattr(server, parameters["type"])(
                **parameters["init_kwargs"]
            )
        return devices

    def start_devices(self):
        for device in self.devices.values():
            device.start()

    def finish(self):
        self.stats.stop_time = datetime.datetime.now()
        if self.is_waiting_to_interrupt():
            self.stats.state = SequenceState.INTERRUPTED
        else:
            self.stats.state = SequenceState.FINISHED
        self.sequence.set_stats(self.stats)

    def record_exception(self):
        self.stats.stop_time = datetime.datetime.now()
        self.stats.state = SequenceState.CRASHED
        self.sequence.set_stats(self.stats)

    def shutdown(self):
        exceptions = []
        for device in self.devices.values():
            try:
                device.shutdown()
            except Exception as error:
                exceptions.append(error)
        if exceptions:
            raise ExceptionGroup("Errors occurred while shutting down", exceptions)
        logger.info("Sequence finished")

    def run_sequence(self):
        """Execute the sequence header and program"""

        with SequenceContext(variables=VariableNamespace()) as context:
            self.run_step(self.experiment_config.header, context)
            self.run_step(self.sequence_config.program, context)

    @singledispatchmethod
    def run_step(self, step: Step, context: SequenceContext):
        """Execute a given step of the sequence

        This function should be implemented for each Step type that can be run on the
        experiment. It should also return as soon as possible if the sequence needs to
        be interrupted.

        Args:
            step: the step of the sequence currently executed
            context: a mutable object that holds information about the sequence being
            run, such as the values of the variables. Step that update variables should
            reflect this by modifying the context.
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
        """Loop over a variable in a numpy arange like loop"""

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
        """Loop over a variable in a numpy linspace like loop"""

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
        except CameraTimeoutError as error:
            logger.warning(
                "A camera timeout error occurred:\n"
                f"{error}\n"
                "Attempting to redo the failed shot"
            )
            for camera in self.get_cameras().values():
                camera.reset_acquisition()
            data = self.do_shot(
                self.sequence_config.shot_configurations[shot.name], context.variables
            )

        old_shot_number = context.shot_numbers.get(shot.name, 0)
        context.shot_numbers[shot.name] = old_shot_number + 1

        shot_file_path = (
            self.sequence.shot_folder
            / f"{shot.name}_{context.shot_numbers[shot.name]}.hdf5"
        )

        t1 = datetime.datetime.now()
        self.stats.number_completed_shots += 1
        self.sequence.set_stats(self.stats)
        logger.info(f"shot executed in {(t1 - t0).total_seconds():.3f} s")
        context.delayed_executor.submit(
            save_shot, shot_file_path, t0, t1, deepcopy(context.variables), data
        )
        logger.debug(context.variables)

    def do_shot(
        self, shot: ShotConfiguration, context: VariableNamespace
    ) -> dict[str, Any]:
        self.prepare_shot(shot, context)
        self.run_shot()
        data = self.extract_data()
        return data

    def prepare_shot(self, shot: ShotConfiguration, context: VariableNamespace):
        device_parameters = compute_shot_parameters(
            self.experiment_config, shot, context
        )
        self.update_device_parameters(device_parameters)

    def update_device_parameters(self, device_parameters: dict[str, dict[str, Any]]):
        future_updates: dict[str, Future] = {}

        with ThreadPoolExecutor() as update_executor:
            for device_name, parameters in device_parameters.items():
                future_updates[device_name] = update_executor.submit(
                    self.devices[device_name].update_parameters, **parameters
                )

        exceptions = []
        for device_name, update in future_updates.items():
            if isinstance(exception := update.exception(), Exception):
                exception.add_note(
                    f"Failed to update device {device_name} with parameters:\n"
                    f"{pprint.pformat(device_parameters[device_name])}"
                )
                exceptions.append(exception)

        if exceptions:
            raise ExceptionGroup(
                "Errors occurred when updating device parameters", exceptions
            )

    def run_shot(self):
        for ni6738_card in self.get_ni6738_cards().values():
            ni6738_card.run()

        future_acquisitions: dict[str, Future] = {}
        with ThreadPoolExecutor() as acquisition_executor:
            for camera_name, camera in self.get_cameras().items():
                future_acquisitions[camera_name] = acquisition_executor.submit(
                    camera.acquire_all_pictures
                )
            for spincore_sequencer in self.get_spincore_sequencers().values():
                spincore_sequencer.run()

        for acquisition in future_acquisitions.values():
            if exception := acquisition.exception():
                raise exception

    def extract_data(self):
        data = {}
        for camera_name, camera in self.get_cameras().items():
            data[camera_name] = camera.read_all_pictures()
        return data

    def get_ni6738_cards(self) -> dict[str, "NI6738AnalogCard"]:
        return {
            device_name: device
            for device_name, device in self.devices.items()
            if isinstance(
                self.experiment_config.get_device_config(device_name),
                NI6738SequencerConfiguration,
            )
        }

    def get_spincore_sequencers(self) -> dict[str, "SpincorePulseBlaster"]:
        return {
            device_name: device
            for device_name, device in self.devices.items()
            if isinstance(
                self.experiment_config.get_device_config(device_name),
                SpincoreSequencerConfiguration,
            )
        }

    def get_cameras(self) -> dict[str, "CCamera"]:
        return {
            device_name: device
            for device_name, device in self.devices.items()
            if isinstance(
                self.experiment_config.get_device_config(device_name),
                CameraConfiguration,
            )
        }

    def is_waiting_to_interrupt(self) -> bool:
        return self._waiting_to_interrupt.is_set()


def save_shot(
    file_path: Path,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    variables: VariableNamespace,
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


def create_remote_device_managers(
    device_server_configs: dict[str, DeviceServerConfiguration]
) -> dict[str, RemoteDeviceClientManager]:
    remote_device_managers: dict[str, RemoteDeviceClientManager] = {}
    for server_name, server_config in device_server_configs.items():
        address = (server_config.address, server_config.port)
        authkey = bytes(server_config.authkey.get_secret_value(), encoding="utf-8")
        remote_device_managers[server_name] = RemoteDeviceClientManager(
            address=address, authkey=authkey
        )
    return remote_device_managers
