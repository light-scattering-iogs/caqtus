from __future__ import annotations

from typing import TYPE_CHECKING

import attrs

from .iteration_configuration import IterationConfiguration
from .shot import Shot
from ..path import BoundSequencePath, PureSequencePath
from ..shot import TimeLanes

if TYPE_CHECKING:
    from ..experiment_session import ExperimentSession


@attrs.frozen(eq=False, order=False)
class Sequence:
    """Contains the runtime information and data of a sequence.

    Only methods that take an ExperimentSession argument actually connect to the
    permanent storage of the experiment. Such methods can raise SequenceNotFoundError if
    the sequence does not exist in the session. They are also expected to be
    comparatively slow since they require a file system access, possibly over the
    network.
    """

    path: BoundSequencePath

    def __str__(self) -> str:
        return str(self.path)

    @property
    def session(self) -> ExperimentSession:
        return self.path.session

    def exists(self) -> bool:
        """Check if the sequence exists in the session."""

        if self.session.paths.does_path_exists(self.path):
            return self.session.sequences.is_sequence(self.path)
        else:
            return False

    def get_iteration_configuration(self) -> IterationConfiguration:
        """Return the iteration configuration of the sequence."""

        return self.session.sequences.get_iteration_configuration(self.path)

    def get_time_lanes(self) -> TimeLanes:
        """Return the time lanes that define how a shot is run for this sequence."""

        return self.session.sequences.get_time_lanes(self.path)

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        """Set the time lanes that define how a shot is run for this sequence."""

        return self.session.sequences.set_time_lanes(self.path, time_lanes)

    def get_shots(self) -> list[Shot]:
        """Return the shots that belong to this sequence."""

        return self.session.sequences.get_shots(self.path)

    def duplicate(self, target_path: PureSequencePath | str) -> Sequence:
        """Duplicate the sequence to a new path.

        The sequence created will be in the draft state and will have the same iteration
        configuration and time lanes as the original sequence.
        """

        if isinstance(target_path, str):
            target_path = PureSequencePath(target_path)

        iteration_configuration = self.get_iteration_configuration()
        time_lanes = self.get_time_lanes()
        return self.session.sequences.create(
            target_path, iteration_configuration, time_lanes
        )

    def __eq__(self, other):
        if isinstance(other, Sequence):
            return self.path == other.path
        else:
            return NotImplemented
