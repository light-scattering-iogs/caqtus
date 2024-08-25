from __future__ import annotations

import datetime
from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional, Self

import attrs
import polars

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.types.data import DataLabel
from caqtus.types.iteration import IterationConfiguration, Unknown
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.timelane import TimeLanes
from caqtus.types.variable_name import DottedVariableName
from .shot import Shot
from .. import TracebackSummary
from .._path import PureSequencePath
from .._return_or_raise import unwrap
from .._sequence_collection import PathIsNotSequenceError
from .._state import State

if TYPE_CHECKING:
    from .._experiment_session import ExperimentSession
    from caqtus.analysis.loading import DataImporter


def _convert_to_path(path: PureSequencePath | str) -> PureSequencePath:
    if isinstance(path, str):
        return PureSequencePath(path)
    return path


@attrs.frozen(eq=False, order=False)
class Sequence:
    """Represent a sequence in the experiment session.

    Sequence objects can be obtained by calling :meth:`ExperimentSession.get_sequence`.
    The returned sequence object is bound to the session and is only valid in the
    context where the session is active.

    Args:
        path: The path of the sequence.
        session: The session to which the sequence belongs.
            The sequence is bound to the session and is only valid in the context where
            the session is active.
    """

    path: PureSequencePath = attrs.field(converter=_convert_to_path)
    session: ExperimentSession

    def __attrs_post_init__(self):
        is_sequence = unwrap(self.session.sequences.is_sequence(self.path))
        if not is_sequence:
            raise PathIsNotSequenceError(self.path)

    @classmethod
    def create(
        cls,
        path: PureSequencePath,
        iteration_configuration: IterationConfiguration,
        time_lanes: TimeLanes,
        session: ExperimentSession,
    ) -> Self:
        """Create a new sequence in the session.

        Args:
            path: The path at which to create the sequence.
            iteration_configuration: How the sequence parameters should be iterated
                over.
            time_lanes: How the shots should be run.
            session: The session in which the sequence should be created.
                The session must be active.
        """

        session.sequences.create(path, iteration_configuration, time_lanes)
        return cls(path, session)

    def __str__(self) -> str:
        return str(self.path)

    def __len__(self) -> int:
        """Return the number of shots that have been run for this sequence."""

        return len(unwrap(self.session.sequences.get_shots(self.path)))

    def get_state(self) -> State:
        """Return the state of the sequence."""

        return unwrap(self.session.sequences.get_state(self.path))

    def get_global_parameters(self) -> ParameterNamespace:
        """Return a copy of the parameter tables set for this sequence.

        Raises:
            RuntimeError: If the sequence is in DRAFT state, since the global parameters
                are only set once the sequence has entered the PREPARING state.
        """

        return self.session.sequences.get_global_parameters(self.path)

    def get_iteration_configuration(self) -> IterationConfiguration:
        """Return the iteration configuration of the sequence."""

        return self.session.sequences.get_iteration_configuration(self.path)

    def get_time_lanes(self) -> TimeLanes:
        """Return the time lanes that define how a shot is run for this sequence."""

        return self.session.sequences.get_time_lanes(self.path)

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        """Set the time lanes that define how a shot is run for this sequence."""

        return self.session.sequences.set_time_lanes(self.path, time_lanes)

    def get_shots(self) -> Iterable[Shot]:
        """Return the shots that belong to this sequence.

        The shots are returned sorted by index.
        """

        pure_shots = unwrap(self.session.sequences.get_shots(self.path))
        sorted_shots = sorted(pure_shots, key=lambda x: x.index)
        return (Shot.bound(shot, self.session) for shot in sorted_shots)

    def get_start_time(self) -> Optional[datetime.datetime]:
        """Return the time the sequence was started.

        If the sequence has not been started, return None.
        """

        return unwrap(self.session.sequences.get_stats(self.path)).start_time

    def get_end_time(self) -> Optional[datetime.datetime]:
        """Return the time the sequence was ended.

        If the sequence has not been ended, return None.
        """

        return unwrap(self.session.sequences.get_stats(self.path)).stop_time

    def get_expected_number_of_shots(self) -> int | Unknown:
        """Return the expected number of shots for the sequence.

        If the sequence has not been started, return None.
        """

        return unwrap(self.session.sequences.get_stats(self.path)).expected_number_shots

    def duplicate(self, target_path: PureSequencePath | str) -> Sequence:
        """Duplicate the sequence to a new path.

        The sequence created will be in the draft state and will have the same iteration
        configuration and time lanes as the original sequence.
        """

        if isinstance(target_path, str):
            target_path = PureSequencePath(target_path)

        iteration_configuration = self.get_iteration_configuration()
        time_lanes = self.get_time_lanes()
        self.create(target_path, iteration_configuration, time_lanes, self.session)
        return Sequence(target_path, self.session)

    def get_device_configurations(self) -> dict[DeviceName, DeviceConfiguration]:
        """Return the device configurations used when the sequence was launched."""

        device_configurations = self.session.sequences.get_device_configurations(
            self.path
        )

        return dict(device_configurations)

    def get_local_parameters(self) -> set[DottedVariableName]:
        """Return the name of the parameters specifically set for this sequence."""

        iterations = self.get_iteration_configuration()
        return iterations.get_parameter_names()

    def get_traceback_summary(self) -> Optional[TracebackSummary]:
        """Return the traceback summary of the sequence.

        Return:
            The summary of the exception that crashed the sequence if one could be
            retrieved, otherwise None.

        Raises:
            SequenceNotCrashedError: If the sequence is not in the CRASHED state.
        """

        return unwrap(self.session.sequences.get_exception(self.path))

    def load_shots_data(
        self,
        importer: "DataImporter",
        tags: Optional[polars.type_aliases.FrameInitTypes] = None,
    ) -> Iterable[polars.DataFrame]:
        """Load the data of the shots that have been run for this sequence.

        Args:
            importer: A function that takes a shot and returns the data of the shot.
                It will be called for each shot in the sequence.
            tags: An optional object that can be converted to a 1-row DataFrame.
                The dataframe will be joined with the data of each shot.
                This allows to add extra information to the dataframes returned for this
                sequence.

        Yields:
            Dataframes containing the data of the shots in the sequence ordered by shot
            index.
        """

        if tags is not None:
            tags_dataframe = polars.DataFrame(tags)
            if len(tags_dataframe) != 1:
                raise ValueError("tags should be a single row DataFrame")
        else:
            tags_dataframe = None

        data_labels = set[DataLabel]()

        for shot in self.get_shots():
            # Here we use a trick to speed up data loading.
            # We keep track of the data labels that have been loaded so far and
            # reload them before passing them to the importer.
            # This ensure that data are queried in group, with is more efficient.
            shot.get_data_by_labels(data_labels)
            data = importer(shot)
            data_labels = set(shot._data_cache.keys())

            if tags is not None:
                yield data.join(tags_dataframe, how="cross")
            else:
                yield data
