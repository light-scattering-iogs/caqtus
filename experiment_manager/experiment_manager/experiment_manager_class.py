import datetime
import logging
import os
import time
from copy import copy
from enum import Enum, auto
from functools import singledispatchmethod
from pathlib import Path
from threading import Thread

import numpy
import yaml
from pint import DimensionalityError
from spincore_sequencer import Instruction, Continue, Loop

from experiment_config import ExperimentConfig
from experiment_config.experiment_config import ReservedChannel
from expression import Expression
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
from shot import Lane, DigitalLane, AnalogLane, ShotConfiguration
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
        with open(self.sequence_path / "sequence_config.yaml", "r") as file:
            self.sequence_config: SequenceConfig = yaml.load(
                file, Loader=YAMLSerializable.get_loader()
            )

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
        with open(self.sequence_path / "sequence_state.yaml", "w") as file:
            file.write(yaml.dump(self.stats, Dumper=YAMLSerializable.get_dumper()))

    def finish(self):
        self.stats.stop_time = datetime.datetime.now()
        self.stats.state = SequenceState.FINISHED
        with open(self.sequence_path / "sequence_state.yaml", "w") as file:
            file.write(yaml.dump(self.stats, Dumper=YAMLSerializable.get_dumper()))

    def record_exception(self):
        self.stats.stop_time = datetime.datetime.now()
        self.stats.state = SequenceState.CRASHED
        with open(self.sequence_path / "sequence_state.yaml", "w") as file:
            file.write(yaml.dump(self.stats, Dumper=YAMLSerializable.get_dumper()))

    def shutdown(self):
        self.parent.set_state(ExperimentState.IDLE)

    def run_sequence(self):
        context: dict[str] = {}
        self.run_step(self.sequence_config.program, context)

    @singledispatchmethod
    def run_step(self, step: Step, context: dict[str]) -> dict[str]:
        raise NotImplementedError(f"run_step is not implemented for {type(step)}")

    @run_step.register
    def _(self, steps: SequenceSteps, context):
        for step in steps.children:
            context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, declaration: VariableDeclaration, context):
        updated_context = copy(context)
        updated_context[declaration.name] = Quantity(
            declaration.expression.evaluate(context | units)
        )
        logger.debug(updated_context)
        return updated_context

    @run_step.register
    def _(self, arange_loop: ArangeLoop, context):
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
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, linspace_loop: LinspaceLoop, context):
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
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, shot: ExecuteShot, context: dict[str]):
        t0 = time.time()
        config = shot.configuration
        self.compile_shot(config, context)

        t1 = time.time()
        logger.info(f"shot executed in {(t1 - t0) * 1e3} ms")
        return context

    def compile_shot(
        self, shot: ShotConfiguration, context: dict[str]
    ) -> list[Instruction]:
        durations = evaluate_step_durations(
            shot.step_names, shot.step_durations, context
        )
        analog_time_step = self.experiment_config.ni6738_analog_sequencer.time_step
        digital_time_step = 10e-9

        # check durations
        for step_name, duration in zip(shot.step_names, durations):
            if duration < digital_time_step:
                raise ValueError(
                    f"Duration of step '{step_name}' ({(duration * ureg.s).to('ns')})"
                    " is too short"
                )

        # computes analog local times for each step
        analog_times = []
        last_analog_time = -numpy.inf
        for duration in durations:
            step_analog_times = numpy.arange(
                max(last_analog_time + analog_time_step, digital_time_step),
                duration - analog_time_step,
                analog_time_step,
            )
            if len(step_analog_times) > 0:
                last_analog_time = step_analog_times[-1]
            last_analog_time -= duration
            analog_times.append(step_analog_times)

        # generate digital instructions
        instructions = []
        digital_lanes = [lane for lane in shot.lanes if isinstance(lane, DigitalLane)]
        # noinspection PyTypeChecker
        analog_clock_channel = self.experiment_config.spincore.get_channel_number(
            ReservedChannel.ni6738_analog_sequencer_variable_clock
        )
        for step in range(len(durations)):
            values = [False] * self.experiment_config.spincore.number_channels
            for lane in digital_lanes:
                channel = self.experiment_config.spincore.get_channel_number(lane.name)
                values[channel] = lane.get_effective_value(step)
            if len(analog_times[step]) > 0:
                duration = analog_times[step][0]
            else:
                duration = durations[step]
            instructions.append(Continue(values=values, duration=duration))
            if len(analog_times[step]) > 0:
                (low_values := copy(values))[analog_clock_channel] = False
                (high_values := copy(low_values))[analog_clock_channel] = True
                instructions.append(
                    Loop(
                        start_values=high_values,
                        start_duration=analog_time_step / 2,
                        end_values=low_values,
                        end_duration=analog_time_step / 2,
                    )
                )
        return instructions


def generate_analog_durations(
    durations: list[float],
    analog_time_step: float,
    lanes: list[Lane],
    context: dict[str],
) -> list[Quantity]:
    last_update_time = -numpy.inf
    times = []
    for step, duration in enumerate(durations):
        is_step_of_constants = all(
            is_constant(lane.get_effective_value(step))
            for lane in lanes
            if isinstance(lane, AnalogLane)
        )
        if is_step_of_constants:
            current_step_times = numpy.zeros(1, dtype=float) * ureg.s
        else:
            current_step_times = numpy.arange(0, duration, analog_time_step) * ureg.s

    return times


def is_constant(expression: Expression):
    return "t" not in expression.upstream_variables


def evaluate_step_durations(
    step_names: list[str], duration_expressions: list[Expression], context: dict[str]
) -> list[float]:
    """Return the list of step durations in seconds"""
    durations = []
    for name, expression in zip(step_names, duration_expressions):
        duration: Quantity = expression.evaluate(context | units)
        try:
            durations.append(duration.to("s").magnitude)
        except DimensionalityError as err:
            err.extra_msg = f" for the duration ({expression.body}) of step '{name}'"
            raise err
    return durations




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
