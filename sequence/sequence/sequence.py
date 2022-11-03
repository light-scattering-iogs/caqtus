import math
from pathlib import Path
from typing import Literal

from experiment_config import ExperimentConfig
from settings_model import YAMLSerializable
from .sequence_config import SequenceConfig, compute_number_shots
from .sequence_state import SequenceState, SequenceStats


class Sequence:
    def __init__(self, path: Path):
        self._path = Path(path)

    @property
    def path(self):
        return self._path

    @property
    def relative_path(self):
        experiment_config: ExperimentConfig = YAMLSerializable.load(
            self._path / "experiment_config.yaml"
        )
        return self._path.relative_to(experiment_config.data_path)

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
            if child.is_file() and child.suffix == ".h5py":
                count += 1

        return count

    # @property
    # def estimate_
