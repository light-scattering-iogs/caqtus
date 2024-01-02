from __future__ import annotations

from typing import TYPE_CHECKING

import attrs

from ..path import BoundSequencePath

if TYPE_CHECKING:
    from ..experiment_session import ExperimentSession


@attrs.frozen
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
            return self.session.sequence_collection.is_sequence(self.path)
        else:
            return False

    # def get_config(self, experiment_session: ExperimentSession) -> SequenceConfig:
    #     """Return the configuration of the sequence.
    #
    #     Whether or not the sequence has been run, it always has a configuration.
    #     """
    #
    #     yaml = experiment_session.sequence_hierarchy.get_sequence_config_yaml(self)
    #     return SequenceConfig.from_yaml(yaml)
    #
    # def set_config(
    #     self, config: SequenceConfig, experiment_session: ExperimentSession
    # ) -> None:
    #     """Set the configuration of the sequence.
    #
    #     If the sequence has already been run, this method will raise `:py:class:SequenceNotEditableError`.
    #     """
    #
    #     if not isinstance(config, SequenceConfig):
    #         raise TypeError(
    #             f"Expected instance of <SequenceConfig>, got {type(config)}"
    #         )
    #
    #     yaml = config.to_yaml()
    #     assert (
    #         SequenceConfig.from_yaml(yaml) == config
    #     )  # will trigger validation before saving
    #
    #     experiment_session.sequence_hierarchy.set_sequence_config_yaml(
    #         self, yaml, config.compute_total_number_of_shots()
    #     )

    # def get_experiment_config(
    #     self, experiment_session: ExperimentSession
    # ) -> Optional[ExperimentConfig]:
    #     """Return the experiment config associated with the sequence.
    #
    #     If the sequence has not been run yet, this method will return None.
    #     If the sequence has been run, this method will return the experiment config that was used to run it.
    #     """
    #
    #     return experiment_session.sequence_hierarchy.get_sequence_experiment_config(
    #         self
    #     )
    #
    # def set_experiment_config(
    #     self, experiment_config: str, experiment_session: ExperimentSession
    # ) -> None:
    #     """Set the experiment config the sequence is referring to.
    #
    #     This method should only be called when the sequence starts running.
    #     """
    #
    #     experiment_session.sequence_hierarchy.set_sequence_experiment_config(
    #         self, experiment_config
    #     )
    #
    # def set_shot_config(
    #     self,
    #     shot_name: str,
    #     shot_config: ShotConfiguration,
    #     experiment_session: ExperimentSession,
    # ) -> None:
    #     """Set the configuration of a shot."""
    #
    #     if not isinstance(shot_config, ShotConfiguration):
    #         raise TypeError(
    #             f"Expected instance of <ShotConfiguration>, got {type(shot_config)}"
    #         )
    #     sequence_config = self.get_config(experiment_session)
    #     sequence_config.shot_configurations[shot_name] = shot_config
    #     self.set_config(sequence_config, experiment_session)
    #
    # def set_steps_program(
    #     self, steps: SequenceSteps, experiment_session: ExperimentSession
    # ) -> None:
    #     """Set the steps of the sequence."""
    #
    #     if not isinstance(steps, SequenceSteps):
    #         raise TypeError(f"Expected instance of <SequenceSteps>, got {type(steps)}")
    #     sequence_config = self.get_config(experiment_session)
    #     sequence_config.program = steps
    #     self.set_config(sequence_config, experiment_session)
    #
    # def get_state(self, experiment_session: ExperimentSession) -> State:
    #     """Returns the state of the sequence."""
    #
    #     return experiment_session.sequence_hierarchy.get_sequence_state(self)
    #
    # def get_shots(self, experiment_session: ExperimentSession) -> list[Shot]:
    #     """Returns the shots that have been run for the sequence."""
    #
    #     return experiment_session.sequence_hierarchy.get_sequence_shots(self)
    #
    # @classmethod
    # def create_sequence(
    #     cls,
    #     path: BoundSequencePath,
    #     sequence_config: SequenceConfig,
    #     experiment_config_name: Optional[str],
    #     experiment_session: ExperimentSession,
    # ) -> Sequence:
    #     """Create a new sequence in the session."""
    #
    #     return experiment_session.sequence_hierarchy.create_sequence(
    #         path, sequence_config, experiment_config_name
    #     )
    #
    # def get_stats(self, experiment_session: ExperimentSession) -> SequenceStats:
    #     result = experiment_session.sequence_hierarchy.get_sequence_stats(self)
    #     return unwrap(result)
    #
    # @classmethod
    # def query_sequence_stats(
    #     cls, sequences: Iterable[Sequence], experiment_session: ExperimentSession
    # ) -> dict[BoundSequencePath, SequenceStats]:
    #     return experiment_session.sequence_hierarchy.query_sequence_stats(sequences)
    #
    # @classmethod
    # def get_all_sequence_names(cls, experiment_session: ExperimentSession) -> set[str]:
    #     """Get all the sequence names within a given session.
    #
    #     Args:
    #         experiment_session: The activated experiment session in which to query the
    #         sequences.
    #     """
    #
    #     return experiment_session.sequence_hierarchy.get_all_sequence_names()


#
# @attrs.frozen
# class SequenceStats:
#     state: State
#     total_number_shots: Optional[int]
#     number_completed_shots: int
#     start_date: Optional[datetime]
#     stop_date: Optional[datetime]


# class SequenceNotEditableError(InvalidSequenceStateError):
#     """
#     Raised when attempting to modify a sequence configuration that is not editable.
#     """
#
#     pass
