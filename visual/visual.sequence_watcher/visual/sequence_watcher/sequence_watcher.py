import logging
import threading
from copy import copy
from datetime import datetime
from typing import Optional, Callable, Any

import pandas

from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.runtime import Sequence, Shot

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequenceWatcher:
    """Class that watches an experimental sequence"""

    def __init__(
        self,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        update_interval: float = 1,
    ):
        self._sequence = sequence
        self._sequence_start_time: Optional[datetime] = None
        self._processed_shots: set[int] = set()
        self._session = session_maker()
        self._update_interval = update_interval

        self._lock = threading.Lock()
        self._must_stop_watching = threading.Event()
        self._watch_thread = threading.Thread(target=self._watch_sequence)

    def __del__(self):
        self.stop()

    def reset(self):
        """Resets the sequence watcher to a clean state"""
        self._sequence_start_time = None
        self._processed_shots = set()

    def start(self):
        """Starts watching the sequence"""
        self.reset()
        self._start_watch_thread()

    def _start_watch_thread(self):
        with self._lock:
            self._must_stop_watching.clear()
            self._watch_thread.start()

    def _watch_sequence(self):
        while not self._must_stop_watching.is_set():
            with self._session.activate() as session:
                stats = self._sequence.get_stats(session)
                shots = self._sequence.get_shots(session)
            if stats["start_date"] != self._sequence_start_time:
                self.reset()
                self._sequence_start_time = stats["start_date"]
            if stats["number_completed_shots"] > len(self._processed_shots):
                new_shots = self._get_new_shots(shots)
                for shot in new_shots:
                    self.process_shot(shot)
                    self._processed_shots.add(shot.index)
                    if self._must_stop_watching.is_set():
                        break
            self._must_stop_watching.wait(self._update_interval)

    def _get_new_shots(self, shots) -> list[Shot]:
        new_shots = []
        for shot in shots:
            if shot.index not in self._processed_shots:
                new_shots.append(shot)
        return new_shots

    def process_shot(self, shot: Shot):
        """Processes a shot"""
        pass

    def stop(self):
        """Stops watching the sequence"""
        self._stop_watch_thread()

    def _stop_watch_thread(self):
        with self._lock:
            self._must_stop_watching.set()
            if self._watch_thread.is_alive():
                self._watch_thread.join()


class DataframeSequenceWatcher(SequenceWatcher):
    """Class that watches an experimental sequence and stores the data in a
    pandas dataframe as they are processed"""

    def __init__(
        self,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
        update_interval: float = 1,
    ):
        super().__init__(sequence, session_maker, update_interval)
        self._dataframe = pandas.DataFrame()
        self._importer = importer

    def reset(self):
        """Resets the dataframe to an empty state"""
        super().reset()
        self._dataframe = pandas.DataFrame()

    def process_shot(self, shot: Shot) -> pandas.Index:
        """Processes a shot"""
        with self._session.activate() as session:
            data = self._importer(shot, session)
        new_index = pandas.MultiIndex.from_tuples(
            [(str(shot.sequence.path), shot.name, shot.index)],
            names=("sequence", "shot", "index"),
        )
        data = pandas.DataFrame([data], index=new_index)
        self._dataframe = pandas.concat((self._dataframe, data))
        return new_index

    def get_dataframe(self) -> pandas.DataFrame:
        """Returns the dataframe"""
        return copy(self._dataframe)
