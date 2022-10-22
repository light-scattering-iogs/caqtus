import datetime
import logging
import os
from enum import Enum, auto
from functools import singledispatchmethod
from pathlib import Path
from threading import Thread

import numpy
import yaml

from experiment_config import ExperimentConfig
from sequence import (
    SequenceStats,
    SequenceState,
    Step,
    SequenceConfig,
    SequenceSteps,
    VariableDeclaration,
)
from sequence.sequence_config import ArangeLoop
from settings_model import YAMLSerializable
from units import units, Q

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentState(Enum):
    IDLE = auto()
    RUNNING = auto()
    WAITING_TO_INTERRUPT = auto()


class SequenceRunnerThread(Thread):
    def __init__(
            self, experiment_config: str, sequence_path: Path,
            parent: "ExperimentManager"
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
        self.context: dict[str] = {}
        self.run_step(self.sequence_config.program)

    @singledispatchmethod
    def run_step(self, step: Step):
        raise NotImplementedError(f"run_step is not implemented for {type(step)}")

    @run_step.register
    def _(self, steps: SequenceSteps):
        for step in steps.children:
            self.run_step(step)

    @run_step.register
    def _(self, declaration: VariableDeclaration):
        self.context[declaration.name] = Q(
            declaration.expression.evaluate(self.context | units)
        )
        logger.debug(self.context)

    @run_step.register
    def _(self, arange_loop: ArangeLoop):
        start = Q(arange_loop.start.evaluate(self.context | units))
        stop = Q(arange_loop.stop.evaluate(self.context | units))
        step = Q(arange_loop.step.evaluate(self.context | units))

        unit = start.units

        for value in numpy.arange(
                start.to(unit).magnitude, stop.to(unit).magnitude,
                step.to(unit).magnitude
        ):
            self.context[arange_loop.name] = value * unit
            for step in arange_loop.children:
                self.run_step(step)


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
