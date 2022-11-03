import math
from copy import copy
from pathlib import Path
from typing import Literal

import numpy
import numpy as np

from experiment_config import ExperimentConfig, get_config_path
from settings_model import YAMLSerializable
from shot import DigitalLane, AnalogLane, evaluate_analog_local_times
from shot import evaluate_step_durations, evaluate_analog_values
from units import ureg
from .sequence_config import SequenceConfig, compute_number_shots, find_shot_config
from .sequence_state import SequenceState, SequenceStats


class Sequence:
    def __init__(self, path: Path):
        self._path = Path(path)

    @property
    def path(self):
        return self._path

    @property
    def relative_path(self):
        return self._path.relative_to(self.experiment_config.data_path)

    @property
    def config(self) -> SequenceConfig:
        return YAMLSerializable.load(self._path / "sequence_config.yaml")

    @property
    def stats(self) -> SequenceStats:
        return YAMLSerializable.load(self._path / "sequence_state.yaml")

    @property
    def state(self) -> SequenceState:
        return self.stats.state

    @property
    def total_number_shots(self) -> int | Literal["unknown"]:
        program = self.config.program
        if math.isnan(num := compute_number_shots(program)):
            return "unknown"
        else:
            return num

    def __len__(self):
        return self.number_completed_shots

    @property
    def number_completed_shots(self) -> int:
        count = 0
        for child in self._path.iterdir():
            if child.is_file() and child.suffix == ".hdf5":
                count += 1

        return count

    @property
    def experiment_config(self) -> ExperimentConfig:
        stored_copy = self._path / "experiment_config.yaml"
        if stored_copy.exists():
            return YAMLSerializable.load(stored_copy)
        else:
            return YAMLSerializable.load(get_config_path())

    def compute_lane_values(
        self, lane_name: str, context: dict[str], shot_name: str = "shot"
    ):
        shot = find_shot_config(self.config.program, shot_name)
        lane = shot.find_lane(lane_name)

        step_durations = evaluate_step_durations(shot, context)
        times = np.zeros(len(step_durations) + 1, dtype=float)
        times[1:] = numpy.cumsum(step_durations)

        if isinstance(lane, DigitalLane):
            values = numpy.array(lane.values + [lane.values[-1]])
            return times * ureg.s, values
        elif isinstance(lane, AnalogLane):
            local_analog_times = evaluate_analog_local_times(
                shot,
                step_durations,
                self.experiment_config.ni6738_analog_sequencer.time_step,
                self.experiment_config.spincore.time_step,
            )
            values = evaluate_analog_values(shot, local_analog_times, context)

            global_analog_times = copy(local_analog_times)
            for i, offset in enumerate(times[:-1]):
                global_analog_times[i] += offset

            concatenated_times = np.concatenate(global_analog_times) * ureg.s

            return np.append(concatenated_times, times[-1] * ureg.s), np.append(
                values[lane.name], values[lane.name][-1]
            )
