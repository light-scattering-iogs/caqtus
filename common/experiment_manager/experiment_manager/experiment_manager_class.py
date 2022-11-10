import datetime
import io
import logging
import os
from copy import copy
from enum import Enum, auto
from functools import singledispatchmethod
from pathlib import Path
from threading import Thread

import h5py
import numpy
import yaml

from experiment_config import ExperimentConfig
from experiment_config.experiment_config import ReservedChannel
from ni6738_analog_card import NI6738AnalogCard
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
            time_step=self.experiment_config.spincore.time_step
        )
        self.ni6738 = NI6738AnalogCard(device_id="Dev1", time_step=self.experiment_config.ni6738_analog_sequencer.time_step)

    def run(self):
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

        self.ni6738.start()

        self.spincore.start()

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
        actions = [self.spincore.shutdown, self.ni6738.shutdown]
        for action in actions:
            try:
                action()
            except Exception:
                logger.error("An error occurred when shutting down", exc_info=True)
        self.parent.set_state(ExperimentState.IDLE)

    def run_sequence(self):
        """Walk through the sequence program and execute each step sequentially"""
        context: dict[str] = {}
        context = self.run_step(self.experiment_config.header, context)
        self.run_step(self.sequence_config.program, context)

    @singledispatchmethod
    def run_step(self, step: Step, context: dict[str]) -> dict[str]:
        """Execute a given step of the sequence

        This function should be implemented for each Step type that can be run on the experiment. It should also return
        as soon as possible if the sequence needs to be interrupted.

        Args:
            step: the step of the sequence currently executed
            context: a dictionary of the current variables names and values at this step

        Returns:
            updated context after the step was executed
        """

        raise NotImplementedError(f"run_step is not implemented for {type(step)}")

    @run_step.register
    def _(self, steps: SequenceSteps, context):
        """Execute each child step sequentially"""

        for step in steps.children:
            if self.is_waiting_to_interrupt():
                return context
            else:
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, declaration: VariableDeclaration, context):
        """Add or update a variable declaration in the context"""

        updated_context = copy(context)
        updated_context[declaration.name] = Quantity(
            declaration.expression.evaluate(context | units)
        )
        return updated_context

    @run_step.register
    def _(self, arange_loop: ArangeLoop, context):
        """Loop over a variable in a numpy arange like loop and execute children steps at each repetition"""
        start = Quantity(arange_loop.start.evaluate(context | units))
        stop = Quantity(arange_loop.stop.evaluate(context | units))
        step = Quantity(arange_loop.step.evaluate(context | units))

        unit = start.units

        context = copy(context)

        for value in numpy.arange(
            start.to(unit).magnitude, stop.to(unit).magnitude, step.to(unit).magnitude
        ):
            context[arange_loop.name] = value * unit
            for step in arange_loop.children:
                if self.is_waiting_to_interrupt():
                    return context
                else:
                    context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, linspace_loop: LinspaceLoop, context):
        """Loop over a variable in a numpy linspace like loop and execute children steps at each repetition"""
        start = Quantity(linspace_loop.start.evaluate(context | units))
        stop = Quantity(linspace_loop.stop.evaluate(context | units))
        num = int(linspace_loop.num)

        unit = start.units

        context = copy(context)

        for value in numpy.linspace(
            start.to(unit).magnitude, stop.to(unit).magnitude, num
        ):
            context[linspace_loop.name] = value * unit
            for step in linspace_loop.children:
                if self.is_waiting_to_interrupt():
                    return context
                else:
                    context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, shot: ExecuteShot, context: dict[str]):
        """Execute a shot on the experiment"""

        t0 = datetime.datetime.now()
        config = self.sequence_config.shot_configurations[shot.name]
        spincore_instructions, analog_values = self.compile_shot(config, context)
        analog_voltages = self.generate_analog_voltages(analog_values)
        self.ni6738.apply_rt_variables(values=analog_voltages)
        self.ni6738.run()
        self.spincore.apply_rt_variables(instructions=spincore_instructions)
        self.spincore.run()
        data = {}
        # time.sleep(0.2)

        t1 = datetime.datetime.now()
        logger.info(f"shot executed in {(t1 - t0)}")
        self.save_shot(shot, t0, t1, context, data)
        self.shot_numbers[shot.name] += 1
        return context

    def is_waiting_to_interrupt(self) -> bool:
        return self.parent.get_state() == ExperimentState.WAITING_TO_INTERRUPT

    def compile_shot(
        self, shot: ShotConfiguration, context: dict[str]
    ) -> tuple[list[Instruction], dict[str, Quantity]]:
        """Return the spincore instructions and the analog values for the ni6738"""
        step_durations = evaluate_step_durations(shot, context)

        self.check_durations(shot, step_durations)

        analog_times = evaluate_analog_local_times(
            shot,
            step_durations,
            self.experiment_config.ni6738_analog_sequencer.time_step,
            self.spincore.time_step,
        )

        instructions = self.generate_digital_instructions(
            shot, step_durations, analog_times
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
    ) -> list[Instruction]:
        analog_time_step = self.experiment_config.ni6738_analog_sequencer.time_step
        instructions = []
        # noinspection PyTypeChecker
        analog_clock_channel = self.experiment_config.spincore.get_channel_number(
            ReservedChannel.ni6738_analog_sequencer_variable_clock
        )
        values = [False] * self.experiment_config.spincore.number_channels
        for step in range(len(step_durations)):
            values = [False] * self.experiment_config.spincore.number_channels
            for lane in shot.digital_lanes:
                channel = self.experiment_config.spincore.get_channel_number(lane.name)
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

    def generate_analog_voltages(self, analog_values: dict[str, Quantity]):
        data_length = 0
        for array in analog_values.values():
            data_length = len(array)
            break
        data = numpy.zeros(
            (NI6738AnalogCard.channel_number, data_length), dtype=numpy.float64
        )

        for name, values in analog_values.items():
            voltages = self.experiment_config.ni6738_analog_sequencer.convert_values_to_voltages(name, values).magnitude
            channel_number = self.experiment_config.ni6738_analog_sequencer.find_channel_index(name)
            data[channel_number] = voltages
        return data


    def save_shot(
        self,
        shot: ExecuteShot,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        context: dict[str, Quantity],
        data: dict[str],
    ):

        data_buffer = io.BytesIO()
        with h5py.File(data_buffer, "w") as file:
            file.attrs["start_time"] = start_time.strftime("%Y-%m-%d-%Hh%Mm%Ss%fus")
            file.attrs["end_time"] = end_time.strftime("%Y-%m-%d-%Hh%Mm%Ss%fus")
            file.create_dataset("variables/names", data=list(context.keys()))
            file.create_dataset(
                "variables/units",
                data=[str(quantity.units) for quantity in context.values()],
            )
            file.create_dataset(
                "variables/magnitudes",
                data=[float(quantity.magnitude) for quantity in context.values()],
            )

        shot_file_name = f"{shot.name}_{self.shot_numbers[shot.name]}.hdf5"
        shot_file_path = self.sequence_path / shot_file_name
        if shot_file_path.is_file():
            raise RuntimeError(
                f"{shot_file_path} already exists and won't be overwritten."
            )
        with open(shot_file_path, "wb") as file:
            file.write(data_buffer.getbuffer())


class ExperimentManager:
    def __init__(self):
        logger.info(f"Started experiment manager in process {os.getpid()}")
        self._state: ExperimentState = ExperimentState.IDLE
        self._sequence_runner_thread = None

    def get_state(self) -> ExperimentState:
        return self._state

    def set_state(self, value):
        self._state = value

    def _sequence_finished(self):
        self._state = ExperimentState.IDLE

    def start_sequence(self, experiment_config: str, sequence_path: Path) -> bool:
        """Attempts to start the sequence

        Return True if the sequence was started, False if not.
        """
        if self._state == ExperimentState.IDLE:
            self._state = ExperimentState.RUNNING
            self._sequence_runner_thread = SequenceRunnerThread(
                experiment_config, sequence_path, self
            )
            self._sequence_runner_thread.start()
            return True
        else:
            return False

    def interrupt_sequence(self) -> bool:
        if self._state == ExperimentState.RUNNING:
            self._state = ExperimentState.WAITING_TO_INTERRUPT
            return True
        return False
