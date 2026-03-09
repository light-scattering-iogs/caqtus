from caqtus.session import PureSequencePath
from caqtus.utils.result import unwrap


def test_get_contained_single_sequence(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        assert unwrap(
            session.sequences.get_contained_sequences(PureSequencePath.root())
        ) == {sequence_path}


def test_get_only_sequences(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        other_path = PureSequencePath(r"\a\b\d")
        unwrap(session.paths.create_path(other_path))

        assert unwrap(
            session.sequences.get_contained_sequences(PureSequencePath.root())
        ) == {sequence_path}


def test_get_multiple_sequences(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        other_path = PureSequencePath(r"\a\b\d")
        session.sequences.create(other_path, steps_configuration, time_lanes)

        assert unwrap(
            session.sequences.get_contained_sequences(PureSequencePath.root())
        ) == {sequence_path, other_path}


def test_get_sequence_non_root_path(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        assert unwrap(
            session.sequences.get_contained_sequences(PureSequencePath(r"\a"))
        ) == {sequence_path}


def test_get_contained_sequence_on_sequence(
    session_maker, steps_configuration, time_lanes
):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        assert unwrap(session.sequences.get_contained_sequences(sequence_path)) == {
            sequence_path
        }


def test_get_contained_sequence_with_sibling_sequence(
    session_maker, steps_configuration, time_lanes
):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a")
        unwrap(session.sequences.create(sequence_path, steps_configuration, time_lanes))

        other_path = PureSequencePath(r"\b")
        unwrap(session.paths.create_path(other_path))

        assert unwrap(session.sequences.get_contained_sequences(other_path)) == set()
