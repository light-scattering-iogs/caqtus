import datetime
import logging
import math
import os.path
import os.path
from copy import copy
from functools import cached_property
from pathlib import Path
from typing import Literal, Any, Optional

import h5py
import numpy
from PyQt5.QtCore import QSaveFile
from watchdog.events import (
    FileSystemEventHandler,
    FileModifiedEvent,
    FileCreatedEvent,
    DirModifiedEvent,
    DirCreatedEvent,
    FileDeletedEvent,
    DirDeletedEvent,
)
from watchdog.observers.api import ObservedWatch
from watchdog.observers.polling import PollingObserver

from experiment_config import ExperimentConfig, get_config_path
from sequence.shot import DigitalLane, AnalogLane, evaluate_analog_local_times
from sequence.shot import evaluate_step_durations, evaluate_analog_values
from settings_model import YAMLSerializable
from units import ureg, Quantity
from .sequence_config import SequenceConfig, compute_number_shots
from .sequence_state import SequenceState, SequenceStats

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class Sequence:
    def __init__(
        self,
        path: Path,
        read_only=True,
    ):
        """Give access to a sequence folder and the underlying information

        If the sequence is instantiated directly, its attributes are frozen to their
        first read value, e.g. the number of shot won't increase even though shots are
        produced. If the sequence is created by using
        sequence_folder_watcher.get_sequence(path), the sequencer watcher instance will
        clear the sequence cache when the sequence folder is updated.

        Args:
            path: the folder containing the sequence configuration and data
        """
        self._path = Path(path)
        if not self._path.is_dir():
            raise NotADirectoryError(f"{path} is not a directory")
        if not self.is_sequence_folder(self._path):
            raise RuntimeError(f"{path} is not a sequence directory")
        self._read_only = read_only

    @property
    def path(self):
        return self._path

    @property
    def relative_path(self):
        return self._path.relative_to(self.experiment_config.data_path)

    @property
    def config_path(self) -> Path:
        return self._path / "sequence_config.yaml"

    @cached_property
    def config(self) -> SequenceConfig:
        return YAMLSerializable.load(self.config_path)

    @property
    def experiment_config_path(self) -> Path:
        return self._path / "experiment_config.yaml"

    @property
    def experiment_config(self) -> ExperimentConfig:
        if self.experiment_config_path.exists():
            path = self.experiment_config_path
        else:
            path = get_config_path()
        return YAMLSerializable.load(path)

    @property
    def stats(self) -> SequenceStats:
        return self._stats

    @cached_property
    def _stats(self) -> SequenceStats:
        return YAMLSerializable.load(self.stats_path)

    @stats.setter
    def stats(self, value: SequenceStats):
        if self._read_only:
            raise ValueError("Sequence is read only")
        if not isinstance(value, SequenceStats):
            raise TypeError(f"Can't set sequence stats to value of type {type(value)}")
        self._commit_stats_to_file(value)
        self.remove_cached_property("_stats")

    def _commit_stats_to_file(self, value: SequenceStats):
        file = QSaveFile(str(self.stats_path))
        try:
            file.open(QSaveFile.OpenModeFlag.WriteOnly)
            file.write(YAMLSerializable.dump(value))
            file.commit()
        except Exception as error:
            file.cancelWriting()
            raise error

    @property
    def stats_path(self) -> Path:
        return self._path / "sequence_state.yaml"

    @property
    def state(self) -> SequenceState:
        return self.stats.state

    @cached_property
    def total_number_shots(self) -> int | Literal["unknown"]:
        program = self.config.program
        if math.isnan(num := compute_number_shots(program)):
            return "unknown"
        else:
            return num

    @cached_property
    def number_completed_shots(self) -> int:
        count = 0
        for child in self._path.iterdir():
            if self._is_shot(child):
                count += 1

        return count

    def __len__(self):
        return self.number_completed_shots

    @property
    def duration(self) -> datetime.timedelta:
        if self.state == SequenceState.DRAFT:
            return datetime.timedelta(seconds=0.0)
        else:
            start_time = self.stats.start_time
            if self.state == SequenceState.RUNNING:
                end_time = datetime.datetime.now()
            else:
                end_time = self.stats.stop_time
            return end_time - start_time

    @property
    def remaining_duration(self) -> datetime.timedelta | Literal["unknown"]:
        if self.number_completed_shots == 0:
            return "unknown"
        else:
            return (
                self.duration
                * (self.total_number_shots - self.number_completed_shots)
                / self.number_completed_shots
            )

    @property
    def shots(self) -> list["Shot"]:
        result = []
        for child in self._path.iterdir():
            if self._is_shot(child):
                result.append(Shot(child.relative_to(self._path), self))
        return result

    def __iter__(self):
        for child in self._path.iterdir():
            if self._is_shot(child):
                yield Shot(child.relative_to(self._path), self)

    def compute_lane_values(
        self, lane_name: str, context: dict[str], shot_name: str = "shot"
    ):
        shot = self.config.shot_configurations[shot_name]
        lane = shot.find_lane(lane_name)

        step_durations = evaluate_step_durations(shot, context)
        times = numpy.zeros(len(step_durations) + 1, dtype=float)
        times[1:] = numpy.cumsum(step_durations)

        if isinstance(lane, DigitalLane):
            values = numpy.array(list(lane.values) + [lane.values[-1]])
            return times * ureg.s, values
        elif isinstance(lane, AnalogLane):
            local_analog_times = evaluate_analog_local_times(
                shot,
                step_durations,
                self.experiment_config.ni6738_config.time_step,
                self.experiment_config.spincore_config.time_step,
            )
            values = evaluate_analog_values(shot, local_analog_times, context)

            global_analog_times = copy(local_analog_times)
            for i, offset in enumerate(times[:-1]):
                global_analog_times[i] += offset

            concatenated_times = numpy.concatenate(global_analog_times) * ureg.s

            return numpy.append(concatenated_times, times[-1] * ureg.s), numpy.append(
                values[lane.name], values[lane.name][-1]
            )

    @staticmethod
    def _is_shot(path: Path):
        return path.is_file() and path.suffix == ".hdf5"

    def remove_cached_property(self, property_: str):
        if property_ in self.__dict__:
            delattr(self, property_)

    @staticmethod
    def is_sequence_folder(path: Path) -> bool:
        return (path / "sequence_state.yaml").exists() and (
            path / "sequence_config.yaml"
        ).exists()

    @staticmethod
    def create_new_sequence(path: Path, config: SequenceConfig):
        """Create a new sequence folder with a given configuration

        The sequence created is in the draft state.
        """
        if (parent_sequence := _get_parent_sequence_folder(path)) is not None:
            raise RuntimeError(
                f"Attempting to create a sequence inside an other sequence folder ({parent_sequence})"
            )
        path.mkdir(parents=True, exist_ok=False)
        YAMLSerializable.dump(config, path / "sequence_config.yaml")
        stats = SequenceStats()
        YAMLSerializable.dump(stats, path / "sequence_state.yaml")


class Shot:
    def __init__(self, relative_path: Path, parent: Sequence):
        self._parent = parent
        self._relative_path = relative_path

    @cached_property
    def runtime_variables(self) -> dict[str, Any]:
        with h5py.File(self.path, "r") as file:
            names = file["variables/names"][:]
            units = file["variables/units"][:]
            magnitudes = file["variables/magnitudes"][:]
            result = {
                name.decode("utf-8"): Quantity(magnitude, units=unit.decode("utf-8"))
                for name, unit, magnitude in zip(names, units, magnitudes)
            }

        return result

    @cached_property
    def data_labels(self) -> tuple[str]:
        result: list[str] = list()

        def update_data(name: str, obj):
            if isinstance(obj, h5py.Dataset):
                result.append(name)

        with h5py.File(self.path, "r") as file:
            file["data"].visititems(update_data)
        return tuple(result)

    def get_data(self, data_label: str):
        with h5py.File(self.path, "r") as file:
            return file[f"data/{data_label}"][:]

    @property
    def path(self) -> Path:
        return self._parent.path / self._relative_path

    @property
    def name(self) -> str:
        return str(self._relative_path).removesuffix(".hdf5")

    @property
    def sequence(self) -> Sequence:
        return self._parent

    @cached_property
    def start_time(self) -> datetime.datetime:
        with h5py.File(self.path, "r") as file:
            start_time = datetime.datetime.strptime(
                file.attrs["start_time"], "%Y-%m-%d-%Hh%Mm%Ss%fus"
            )
            return start_time

    @cached_property
    def end_time(self) -> datetime.datetime:
        with h5py.File(self.path, "r") as file:
            start_time = datetime.datetime.strptime(
                file.attrs["start_time"], "%Y-%m-%d-%Hh%Mm%Ss%fus"
            )
            return start_time


class SequenceFolderWatcher(FileSystemEventHandler):
    def __init__(self, data_folder: Path):
        self._data_folder = data_folder

        self._sequence_cache: dict[str, tuple[Sequence, ObservedWatch]] = {}

        self._observer = PollingObserver(timeout=1)
        self._observer.start()
        self.events = []

    @property
    def data_folder(self):
        return self._data_folder

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent):
        if isinstance(event, FileModifiedEvent):
            file_path = Path(event.src_path)
            parent = file_path.parent
            if normalize_path(parent) in self._sequence_cache:
                sequence = self._sequence_cache[normalize_path(parent)][0]
                if file_path == sequence.stats_path:
                    sequence.remove_cached_property("_stats")
                elif file_path == sequence.config_path:
                    sequence.remove_cached_property("config")
                    sequence.remove_cached_property("total_number_shots")

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent):
        if isinstance(event, FileCreatedEvent):
            file_path = Path(event.src_path)
            parent = file_path.parent
            if normalize_path(parent) in self._sequence_cache:
                sequence = self._sequence_cache[normalize_path(parent)][0]
                if file_path.suffix == ".hdf5":
                    # noinspection PyPropertyAccess
                    sequence.number_completed_shots += 1

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent):
        if isinstance(event, DirDeletedEvent):
            _, watch = self._sequence_cache.pop(
                normalize_path(event.src_path), (None, None)
            )
            if watch is not None:
                self._observer.unschedule(watch)
        elif isinstance(event, FileDeletedEvent):
            file_path = Path(event.src_path)
            parent = file_path.parent
            if normalize_path(parent) in self._sequence_cache:
                sequence = self._sequence_cache[normalize_path(parent)][0]
                if file_path.suffix == ".hdf5":
                    sequence.remove_cached_property("number_completed_shots")

    def get_sequence(self, path: Path) -> Sequence:
        if normalize_path(path) in self._sequence_cache:
            return self._sequence_cache[normalize_path(path)][0]
        else:
            watch = self._observer.schedule(self, str(path), recursive=True)
            sequence = Sequence(path)
            self._sequence_cache[normalize_path(path)] = (sequence, watch)
            return sequence

    def is_sequence_folder(self, path: Path) -> bool:
        if normalize_path(path) in self._sequence_cache:
            return True
        else:
            return Sequence.is_sequence_folder(path)


def normalize_path(path: Path):
    return os.path.normpath(path)


def _get_parent_sequence_folder(path: Path) -> Optional[Path]:
    """Return a parent folder of the path that is a sequence folder, if there is one"""
    parent_sequence = None
    for parent in path.parents:
        if Sequence.is_sequence_folder(parent):
            parent_sequence = parent
            break
    return parent_sequence
