import datetime
import logging
import pprint
import time
import typing
from concurrent.futures import ThreadPoolExecutor, Future
from functools import singledispatchmethod
from threading import Thread, Event
from typing import Any

import numpy
import numpy as np
from camera.configuration import CameraConfiguration
from camera.runtime import CameraTimeoutError
from experiment.configuration import (
    SpincoreSequencerConfiguration,
    DeviceServerConfiguration,
)
from experiment.session import ExperimentSessionMaker
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
    OptimizationLoop,
)
from sequence.runtime import SequencePath, Sequence
from sql_model import State
from units import Quantity, units

from device import RuntimeDevice
from variable import VariableNamespace
from .compute_shot_parameters import compute_shot_parameters
from .initialize_devices import get_devices_initialization_parameters
from .run_optimization import Optimizer, CostEvaluatorProcess
from .sequence_context import SequenceContext
from .shot_saver import ShotSaver

if typing.TYPE_CHECKING:
    from ni6738_analog_card.runtime import NI6738AnalogCard
    from camera.runtime import CCamera
    from spincore_sequencer.runtime import SpincorePulseBlaster

# If MOCK_EXPERIMENT is set to True, the experiment will not run the real
# hardware. It will not connect to the device servers but will still compute all
# devices parameters if possible.
# Parameters will be saved, but there will be no data acquisition.

MOCK_EXPERIMENT = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SequenceRunnerThread(Thread):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
        waiting_to_interrupt: Event,
    ):
        super().__init__(name=f"thread_{str(sequence_path)}")
        self._session = session_maker()
        self._session_maker = session_maker
        self._sequence = Sequence(sequence_path)
        self._waiting_to_interrupt = waiting_to_interrupt
        self._remote_device_managers: dict[str, RemoteDeviceClientManager] = {}
        self._devices: dict[str, RuntimeDevice] = {}

        with self._session.activate() as session:
            self._experiment_config = session.get_experiment_config(
                experiment_config_name
            )
            self._sequence_config = self._sequence.get_config(session)
            self._sequence.set_experiment_config(experiment_config_name, session)
            self._sequence.set_state(State.PREPARING, session)

    def run(self):
        try:
            self.prepare()
            self.run_sequence()
            self.finish()
        except Exception:
            self.record_exception()
            logger.error("An error occurred while running the sequence", exc_info=True)
            raise
        finally:
            self.shutdown()

    def prepare(self):
        self._remote_device_managers = create_remote_device_managers(
            self._experiment_config.device_servers
        )
        self.connect_to_device_servers()

        self._devices = self.create_devices()
        self.start_devices()

        with self._session.activate() as session:
            self._sequence.set_state(State.RUNNING, session)

    def connect_to_device_servers(self):
        """Start the connection to the device servers"""
        if MOCK_EXPERIMENT:
            return

        for server_name, server in self._remote_device_managers.items():
            logger.info(f"Connecting to device server {server_name}...")
            try:
                server.connect()
            except ConnectionRefusedError as error:
                raise ConnectionRefusedError(
                    f"The remote server '{server_name}' rejected the connection. It is possible "
                    f"that the server is not running or that the port is not open."
                ) from error
            logger.info(f"Connection established to {server_name}")

    def create_devices(self) -> dict[str, RuntimeDevice]:
        """Instantiate the devices on their respective remote server"""

        if MOCK_EXPERIMENT:
            return {}

        devices = {}
        for name, parameters in get_devices_initialization_parameters(
            self._experiment_config, self._sequence_config
        ).items():
            server = self._remote_device_managers[parameters["server"]]
            devices[name] = getattr(server, parameters["type"])(
                **parameters["init_kwargs"]
            )
        return devices

    def start_devices(self):
        for device_name, device in self._devices.items():
            try:
                device.start()
            except Exception:
                logger.error(f"An error occurred while starting device {device_name}")
                raise

    def finish(self):
        with self._session as session:
            if self.is_waiting_to_interrupt():
                self._sequence.set_state(State.INTERRUPTED, session)
            else:
                self._sequence.set_state(State.FINISHED, session)

    def record_exception(self):
        with self._session:
            self._sequence.set_state(State.CRASHED, self._session)

    def shutdown(self):
        exceptions = []
        for device in self._devices.values():
            try:
                device.shutdown()
            except Exception as error:
                exceptions.append(error)
        if exceptions:
            raise ExceptionGroup("Errors occurred while shutting down", exceptions)
        logger.info("Sequence finished")

    def run_sequence(self):
        """Execute the sequence header and program"""

        context = SequenceContext(variables=VariableNamespace())
        with ShotSaver(self._sequence, self._session_maker) as shot_saver:
            self.run_step(self._experiment_config.header, context, shot_saver)
            self.run_step(self._sequence_config.program, context, shot_saver)

    @singledispatchmethod
    def run_step(self, step: Step, context: SequenceContext, shot_saver: ShotSaver):
        """Execute a given step of the sequence

        This function should be implemented for each Step type that can be run on the
        experiment. It should also return as soon as possible if the sequence needs to
        be interrupted.

        Args:
            step: the step of the sequence currently executed
            context: a mutable object that holds information about the sequence being
            run, such as the values of the variables. Step that update variables should
            reflect this by modifying the context.
            shot_saver: a ShotSaver object that is passed down to the children steps and is used to store shot data in
            order.

        """

        raise NotImplementedError(f"run_step is not implemented for {type(step)}")

    @run_step.register
    def _(self, steps: SequenceSteps, context: SequenceContext, shot_saver: ShotSaver):
        """Execute each child step sequentially"""

        for step in steps.children:
            if self.is_waiting_to_interrupt():
                return
            else:
                self.run_step(step, context, shot_saver)

    @run_step.register
    def _(
        self, declaration: VariableDeclaration, context: SequenceContext, _: ShotSaver
    ):
        """Add or update a variable declaration in the context"""

        context.variables[declaration.name] = Quantity(
            declaration.expression.evaluate(context.variables | units)
        )

    @run_step.register
    def _(
        self, arange_loop: ArangeLoop, context: SequenceContext, shot_saver: ShotSaver
    ):
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
                    self.run_step(step, context, shot_saver)

    @run_step.register
    def _(
        self,
        linspace_loop: LinspaceLoop,
        context: SequenceContext,
        shot_saver: ShotSaver,
    ):
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
                    self.run_step(step, context, shot_saver)

    @run_step.register
    def _(
        self,
        optimization_loop: OptimizationLoop,
        context: SequenceContext,
        shot_saver: ShotSaver,
    ):
        optimizer_config = self._experiment_config.get_optimizer_config(
            optimization_loop.optimizer_name
        )
        optimizer = Optimizer(optimization_loop.variables, context.variables | units)
        shot_saver.wait()
        with CostEvaluatorProcess(self._sequence, optimizer_config) as evaluator:
            while not evaluator.is_ready():
                if self.is_waiting_to_interrupt():
                    evaluator.interrupt()
                    return
            for loop_iteration in range(optimization_loop.repetitions):
                old_shots = shot_saver.saved_shots
                new_values = optimizer.suggest_values()
                context.variables |= new_values

                for step in optimization_loop.children:
                    self.run_step(step, context, shot_saver)
                    if self.is_waiting_to_interrupt():
                        return
                shot_saver.wait()

                new_shots = shot_saver.saved_shots[len(old_shots) :]
                score = evaluator.compute_score(new_shots)
                logger.info(f"Values for iteration {loop_iteration}: {new_values}")
                logger.info(f"Score for iteration {loop_iteration}: {score}")
                optimizer.register(new_values, score)
                with self._session.activate():
                    for shot in new_shots:
                        shot.add_scores(
                            {optimization_loop.optimizer_name: score}, self._session
                        )

    @run_step.register
    def _(self, shot: ExecuteShot, context: SequenceContext, shot_saver: ShotSaver):
        """Execute a shot on the experiment"""

        start_time = datetime.datetime.now()
        try:
            data = self.do_shot(
                self._sequence_config.shot_configurations[shot.name], context.variables
            )
        except CameraTimeoutError as error:
            logger.warning(
                "A camera timeout error occurred:\n"
                f"{error}\n"
                "Attempting to redo the failed shot"
            )
            data = self.do_shot(
                self._sequence_config.shot_configurations[shot.name], context.variables
            )

        end_time = datetime.datetime.now()
        logger.info(
            f"Shot total duration: {(end_time - start_time).total_seconds()*1e3:.1f} ms"
        )

        shot_saver.push_shot(shot.name, start_time, end_time, context.variables, data)

    def do_shot(
        self, shot: ShotConfiguration, context: VariableNamespace
    ) -> dict[str, Any]:
        self.prepare_shot(shot, context)
        self.run_shot()
        data = self.extract_data()
        return data

    def prepare_shot(self, shot: ShotConfiguration, context: VariableNamespace):
        initial_time = datetime.datetime.now()
        device_parameters = compute_shot_parameters(
            self._experiment_config, shot, context
        )
        computation_time = datetime.datetime.now()
        logger.info(
            f"Shot parameters computation duration: {(computation_time - initial_time).total_seconds() * 1e3:.1f} ms"
        )
        self.update_device_parameters(device_parameters)
        update_time = datetime.datetime.now()
        logger.info(
            f"Device parameters update duration: {(update_time - computation_time).total_seconds() * 1e3:.1f} ms"
        )

    def update_device_parameters(self, device_parameters: dict[str, dict[str, Any]]):
        if MOCK_EXPERIMENT:
            return
        future_updates: dict[str, Future] = {}

        with ThreadPoolExecutor() as update_executor:
            for device_name, parameters in device_parameters.items():
                future_updates[device_name] = update_executor.submit(
                    self._devices[device_name].update_parameters, **parameters
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

    def run_shot(self) -> None:
        start_time = datetime.datetime.now()
        if MOCK_EXPERIMENT:
            time.sleep(0.5)
            return
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
        stop_time = datetime.datetime.now()
        logger.info(
            f"Shot execution duration: {(stop_time - start_time).total_seconds() * 1e3:.1f} ms"
        )

    def extract_data(self):
        if MOCK_EXPERIMENT:
            return {
                "image": np.random.uniform(0, 2**15, (100, 100)).astype(np.uint16)
            }

        data = {}
        for camera_name, camera in self.get_cameras().items():
            data[camera_name] = camera.read_all_pictures()
        return data

    def get_ni6738_cards(self) -> dict[str, "NI6738AnalogCard"]:
        return {
            device_name: device  # type: ignore
            for device_name, device in self._devices.items()
            if isinstance(
                self._experiment_config.get_device_config(device_name),
                NI6738SequencerConfiguration,
            )
        }

    def get_spincore_sequencers(self) -> dict[str, "SpincorePulseBlaster"]:
        return {
            device_name: device  # type: ignore
            for device_name, device in self._devices.items()
            if isinstance(
                self._experiment_config.get_device_config(device_name),
                SpincoreSequencerConfiguration,
            )
        }

    def get_cameras(self) -> dict[str, "CCamera"]:
        return {
            device_name: device  # type: ignore
            for device_name, device in self._devices.items()
            if isinstance(
                self._experiment_config.get_device_config(device_name),
                CameraConfiguration,
            )
        }

    def is_waiting_to_interrupt(self) -> bool:
        return self._waiting_to_interrupt.is_set()


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
