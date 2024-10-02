"""Contains the copy function to transfer data between two sessions."""

from typing import assert_type

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
    SequenceNotCrashedError,
)
from caqtus.session._shot_id import ShotId
from caqtus.utils._result import (
    Success,
    Failure,
    is_failure,
    is_failure_type,
    is_success,
    unwrap,
)


def copy_path(
    path: PureSequencePath,
    source_session: ExperimentSession,
    destination_session: ExperimentSession,
) -> Success[None] | Failure[PathIsSequenceError] | Failure[PathNotFoundError]:
    path_creation_result = destination_session.paths.create_path(path)
    if is_failure(path_creation_result):
        return path_creation_result
    created_paths = path_creation_result.value
    for created_path in created_paths:
        creation_date_result = source_session.paths.get_path_creation_date(created_path)
        assert not is_failure_type(creation_date_result, PathIsRootError)
        if is_failure(creation_date_result):
            return creation_date_result
        creation_date = creation_date_result.value
        destination_session.paths.update_creation_date(created_path, creation_date)
    children_result = source_session.paths.get_children(path)
    if is_failure_type(children_result, PathNotFoundError):
        return children_result
    elif is_failure_type(children_result, PathIsSequenceError):
        pass
    else:
        children = children_result.value
        for child in children:
            copy_path(child, source_session, destination_session)


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
    set_state(destination, State.PREPARING, destination_session)
    destination_session.sequences.set_global_parameters(
        destination, source_session.sequences.get_global_parameters(source)
    )
    set_state(destination, State.RUNNING, destination_session)

    for shot_index in range(stats.number_completed_shots):
        shot_parameters = source_session.sequences.get_shot_parameters(
            source, shot_index
        )
        shot_data = source_session.sequences.get_all_shot_data(source, shot_index)
        shot_start_time = source_session.sequences.get_shot_start_time(
            source, shot_index
        )
        shot_stop_time = source_session.sequences.get_shot_end_time(source, shot_index)
        unwrap(
            destination_session.sequences.create_shot(
                ShotId(destination, shot_index),
                shot_parameters,
                shot_data,
                shot_start_time,
                shot_stop_time,
            )
        )

    if state == State.FINISHED:
        set_state(destination, State.FINISHED, destination_session)

    if state == State.INTERRUPTED:
        set_state(destination, State.INTERRUPTED, destination_session)

    if state == State.CRASHED:
        set_state(destination, State.CRASHED, destination_session)
        exception_result = source_session.sequences.get_exception(source)
        assert not is_failure_type(exception_result, PathNotFoundError)
        assert not is_failure_type(exception_result, PathIsNotSequenceError)
        assert not is_failure_type(exception_result, SequenceNotCrashedError)
        exception = exception_result.value

        if exception:
            assert is_success(
                destination_session.sequences.set_exception(destination, exception)
            )
    destination_session.sequences.update_start_and_end_time(
        destination, stats.start_time, stats.stop_time
    )

    return Success(None)


def set_state(path: PureSequencePath, state: State, session: ExperimentSession) -> None:
    result = session.sequences.set_state(path, state)
    assert not is_failure_type(result, PathNotFoundError)
    assert not is_failure_type(result, PathIsNotSequenceError)
    assert_type(result, Success[None])
