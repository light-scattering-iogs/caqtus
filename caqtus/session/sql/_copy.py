"""Contains the copy function to transfer data between two sessions."""

from caqtus.session import (
    PureSequencePath,
    ExperimentSession,
    PathNotFoundError,
    PathIsNotSequenceError,
    PathIsSequenceError,
    PathHasChildrenError,
    PathIsRootError,
    State,
    SequenceStateError,
)
from caqtus.utils._result import Success, Failure, is_failure, is_failure_type


def copy_sequence(
    source: PureSequencePath,
    source_session: ExperimentSession,
    destination: PureSequencePath,
    destination_session: ExperimentSession,
) -> (
    Success[None]
    | Failure[PathNotFoundError]
    | Failure[PathIsNotSequenceError]
    | Failure[PathIsSequenceError]
    | Failure[PathHasChildrenError]
    | Failure[SequenceStateError]
):
    """Copy the sequence from the source to the destination."""

    sequence_stats_result = source_session.sequences.get_stats(source)
    if is_failure(sequence_stats_result):
        return sequence_stats_result
    stats = sequence_stats_result.value
    state = stats.state
    if state not in {State.DRAFT, State.FINISHED, State.INTERRUPTED, State.CRASHED}:
        return Failure(SequenceStateError())
    creation_date = source_session.paths.get_path_creation_date(source)
    assert not is_failure_type(creation_date, PathNotFoundError)
    assert not is_failure_type(creation_date, PathIsRootError)
    iterations = source_session.sequences.get_iteration_configuration(source)
    time_lanes = source_session.sequences.get_time_lanes(source)

    creation_result = destination_session.sequences.create(
        destination, iterations, time_lanes
    )
    if is_failure(creation_result):
        return creation_result
    destination_session.paths.update_creation_date(destination, creation_date.value)

    if state == State.DRAFT:
        return Success(None)
    destination_session.sequences.set_state(destination, State.PREPARING)
    destination_session.sequences.set_global_parameters(
        destination, source_session.sequences.get_global_parameters(source)
    )
    destination_session.sequences.set_state(destination, State.RUNNING)

    for shot in range(stats.number_completed_shots):
        shot_parameters = source_session.sequences.get_shot_parameters(source, shot)
        shot_data = source_session.sequences.get_all_shot_data(source, shot)
        shot_start_time = source_session.sequences.get_shot_start_time(source, shot)
        shot_stop_time = source_session.sequences.get_shot_end_time(source, shot)
        destination_session.sequences.create_shot(
            destination,
            shot,
            shot_parameters,
            shot_data,
            shot_start_time,
            shot_stop_time,
        )

    if state == State.FINISHED:
        destination_session.sequences.set_state(destination, State.FINISHED)

    if state == State.INTERRUPTED:
        destination_session.sequences.set_state(destination, State.INTERRUPTED)

    if state == State.CRASHED:
        destination_session.sequences.set_state(destination, State.CRASHED)
        exceptions = source_session.sequences.get_exception(source).unwrap()
        if exceptions:
            destination_session.sequences.set_exception(destination, exceptions)
    destination_session.sequences.update_start_and_end_time(
        destination, stats.start_time, stats.stop_time
    )

    return Success(None)
