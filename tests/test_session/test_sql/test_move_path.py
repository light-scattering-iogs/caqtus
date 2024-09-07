import pytest

from caqtus.session import PureSequencePath, PathIsSequenceError
from caqtus.session._path_hierarchy import PathExistsError, RecursivePathMoveError


def test_move_single_node(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root() / "dst"

        session.paths.move(src, dst)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(src)
        assert session.paths.does_path_exists(dst)


def test_move_to_subpath(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root() / "dst" / "subpath"

        session.paths.move(src, dst)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(src)
        assert session.paths.does_path_exists(dst)


def test_move_inside_itself(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)

        dst = src / "subpath"
        with pytest.raises(RecursivePathMoveError):
            session.paths.move(src, dst).unwrap()

        session.paths.check_valid()

        assert session.paths.does_path_exists(src)
        assert not session.paths.does_path_exists(dst)


def test_move_on_itself(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)

        with pytest.raises(RecursivePathMoveError):
            session.paths.move(src, src).unwrap()

        session.paths.check_valid()

        assert session.paths.does_path_exists(src)


def test_move_sequence(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        sequence_path = PureSequencePath.root() / "sequence"

        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        dst = PureSequencePath.root() / "dst"
        session.paths.move(sequence_path, dst)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(sequence_path)
        assert session.sequences.is_sequence(dst).unwrap()
        assert session.sequences.get_iteration_configuration(dst) == steps_configuration
        assert session.sequences.get_time_lanes(dst) == time_lanes


def test_cant_move_root(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root()
        dst = PureSequencePath.root() / "dst"

        with pytest.raises(RecursivePathMoveError):
            session.paths.move(src, dst).unwrap()

        session.paths.check_valid()


def test_cant_move_on_root(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root()

        with pytest.raises(PathExistsError):
            session.paths.move(src, dst).unwrap()

        session.paths.check_valid()


def test_cant_move_to_existing_path(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root() / "dst"
        session.paths.create_path(dst)

        with pytest.raises(PathExistsError):
            session.paths.move(src, dst).unwrap()

        session.paths.check_valid()


def test_cant_move_with_sequence_in_dst_path(
    session_maker, steps_configuration, time_lanes
):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)

        sequence_path = PureSequencePath.root() / "sequence"

        session.sequences.create(sequence_path, steps_configuration, time_lanes)

        dst = sequence_path / "dst"
        with pytest.raises(PathIsSequenceError):
            session.paths.move(src, dst).unwrap()
