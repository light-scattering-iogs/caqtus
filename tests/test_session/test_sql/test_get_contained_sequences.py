from caqtus.session import PureSequencePath


def test_get_contained_single_sequence(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        assert session.sequences.get_contained_sequences(
            PureSequencePath.root()
        ).unwrap() == {sequence_path}


def test_get_only_sequences(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        other_path = PureSequencePath(r"\a\b\d")
        session.paths.create_path(other_path).unwrap()

        assert session.sequences.get_contained_sequences(
            PureSequencePath.root()
        ).unwrap() == {sequence_path}


def test_get_multiple_sequences(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        other_path = PureSequencePath(r"\a\b\d")
        session.sequences.create(other_path, steps_configuration, time_lanes)

        assert session.sequences.get_contained_sequences(
            PureSequencePath.root()
        ).unwrap() == {sequence_path, other_path}


def test_get_sequence_non_root_path(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        assert session.sequences.get_contained_sequences(
            PureSequencePath(r"\a")
        ).unwrap() == {sequence_path}


def test_get_contained_sequence_on_sequence(
    session_maker, steps_configuration, time_lanes
):
    with session_maker() as session:
        sequence_path = PureSequencePath(r"\a\b\c")
        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        assert session.sequences.get_contained_sequences(sequence_path).unwrap() == {
            sequence_path
        }
