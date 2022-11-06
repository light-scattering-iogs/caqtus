import datetime
import logging
import math
from copy import copy
from functools import cached_property
from pathlib import Path
from typing import Literal, Any
from weakref import WeakValueDictionary

import h5py
import numpy
from watchdog.events import (
    FileSystemEventHandler,
    FileSystemEvent,
    FileModifiedEvent,
    FileCreatedEvent,
)
from watchdog.observers.polling import PollingObserver

from experiment_config import ExperimentConfig, get_config_path
from settings_model import YAMLSerializable
from shot import DigitalLane, AnalogLane, evaluate_analog_local_times
from shot import evaluate_step_durations, evaluate_analog_values
from units import ureg, Quantity
from .sequence_config import SequenceConfig, compute_number_shots, find_shot_config
from .sequence_state import SequenceState, SequenceStats

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class DataFolderModifiedEventHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self._sequence_references: WeakValueDictionary[
            str, Sequence
        ] = WeakValueDictionary()

    def on_any_event(self, event: FileSystemEvent):
        event_path = Path(event.src_path)
        if event_path.is_dir():
            sequence_path = event_path
        else:
            sequence_path = event_path.parent
        try:
            self._sequence_references[sequence_path].local_files_changed(event)
        except KeyError:
            pass

    def register_sequence(self, sequence: "Sequence"):
        self._sequence_references[sequence.path] = sequence


data_folder_observer = PollingObserver(timeout=1)
event_dispatcher = DataFolderModifiedEventHandler()

experiment_config: ExperimentConfig = YAMLSerializable.load(get_config_path())

data_folder_observer.schedule(
    event_dispatcher, str(experiment_config.data_path), recursive=True
)
data_folder_observer.start()


class Sequence:
    def __init__(self, path: Path, monitoring=False):
        """Dynamical sequence watcher

        This class gives access to a sequence folder and all the underlying information. If monitoring is set to True,
        it updates its attributes to reflect the changes happening on the sequence. If monitoring is False, the sequence
        freezes its attributes to their first read values.
        """
        self._monitoring = monitoring
        self._path = Path(path)
        if not self._path.is_dir():
            raise NotADirectoryError(f"{path} is not a sequence directory")

        self.events = []
        self._number_completed_shots = self.get_number_completed_shots()

        event_dispatcher.register_sequence(self)

    @property
    def path(self):
        return self._path

    @property
    def relative_path(self):
        return self._path.relative_to(self.experiment_config.data_path)

    @cached_property
    def config(self) -> SequenceConfig:
        return YAMLSerializable.load(self._path / "sequence_config.yaml")

    @cached_property
    def stats(self) -> SequenceStats:
        return YAMLSerializable.load(self._path / "sequence_state.yaml")

    def remove_cached_property(self, property_: str):
        if hasattr(self, property_):
            delattr(self, property_)

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

    def get_number_completed_shots(self) -> int:
        count = 0
        for child in self._path.iterdir():
            if self._is_shot(child):
                count += 1

        return count

    @property
    def number_completed_shots(self):
        return self._number_completed_shots

    def local_files_changed(self, event: FileSystemEvent):
        if isinstance(event, FileModifiedEvent):
            if event.src_path == str(self.path / "sequence_state.yaml"):
                self.remove_cached_property("stats")
            elif event.src_path == str(self.path / "sequence_config.yaml"):
                self.remove_cached_property("config")

        elif isinstance(event, FileCreatedEvent):
            if Path(event.src_path).suffix == ".hdf5":
                self._number_completed_shots += 1

    @property
    def experiment_config(self) -> ExperimentConfig:
        stored_copy = self._path / "experiment_config.yaml"
        if stored_copy.exists():
            return YAMLSerializable.load(stored_copy)
        else:
            return YAMLSerializable.load(get_config_path())

    @property
    def shots(self) -> list["Shot"]:
        result = []
        for child in self._path.iterdir():
            if self._is_shot(child):
                result.append(Shot(child.relative_to(self._path), self))
        return result

    @staticmethod
    def _is_shot(path: Path):
        return path.is_file() and path.suffix == ".hdf5"

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

    def compute_lane_values(
        self, lane_name: str, context: dict[str], shot_name: str = "shot"
    ):
        shot = find_shot_config(self.config.program, shot_name)
        lane = shot.find_lane(lane_name)

        step_durations = evaluate_step_durations(shot, context)
        times = numpy.zeros(len(step_durations) + 1, dtype=float)
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

            concatenated_times = numpy.concatenate(global_analog_times) * ureg.s

            return numpy.append(concatenated_times, times[-1] * ureg.s), numpy.append(
                values[lane.name], values[lane.name][-1]
            )

    # def on_modified(self, event):
    #     if isinstance(event, FileModifiedEvent):
    #         if event.src_path == str(self._sequence.path / "sequence_state.yaml"):
    #             self._sequence.remove_cached_property("stats")
    #         elif event.src_path == str(self._sequence.path / "sequence_config.yaml"):
    #             self._sequence.remove_cached_property("config")
    #
    # def on_created(self, event):
    #     if isinstance(event, FileCreatedEvent):
    #         if Path(event.src_path).suffix == ".hdf5":
    #             self._sequence._number_completed_shots += 1
    #             # self._sequence.remove_cached_property("number_completed_shots")


class Shot:
    def __init__(self, relative_path: Path, parent: Sequence):
        self._parent = parent
        self._relative_path = relative_path

    @cached_property
    def runtime_variable(self) -> dict[str, Any]:
        with h5py.File(self.path, "r") as file:
            names = file["variables/names"][:]
            units = file["variables/units"][:]
            magnitudes = file["variables/magnitudes"][:]
            result = {
                name.decode("utf-8"): Quantity(magnitude, units=unit.decode("utf-8"))
                for name, unit, magnitude in zip(names, units, magnitudes)
            }

        return result

    @property
    def path(self) -> Path:
        return self._parent.path / self._relative_path
