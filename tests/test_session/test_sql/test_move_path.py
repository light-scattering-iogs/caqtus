import pytest

from caqtus.session import PureSequencePath, PathIsSequenceError
from caqtus.session._path_hierarchy import PathExistsError, RecursivePathMoveError
from caqtus.session._sequence_collection import SequenceRunningError
from caqtus.types.parameter import ParameterNamespace
from caqtus.utils.result import unwrap


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
            unwrap(session.paths.move(src, dst))

        session.paths.check_valid()

        assert session.paths.does_path_exists(src)
        assert not session.paths.does_path_exists(dst)


def test_move_on_itself(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)

        with pytest.raises(RecursivePathMoveError):
            unwrap(session.paths.move(src, src))

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
        assert unwrap(session.sequences.is_sequence(dst))
        assert session.sequences.get_iteration_configuration(dst) == steps_configuration
        assert session.sequences.get_time_lanes(dst) == time_lanes


def test_cant_move_root(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root()
        dst = PureSequencePath.root() / "dst"

        with pytest.raises(RecursivePathMoveError):
            unwrap(session.paths.move(src, dst))

        session.paths.check_valid()


def test_cant_move_on_root(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root()

        with pytest.raises(PathExistsError):
            unwrap(session.paths.move(src, dst))

        session.paths.check_valid()


def test_cant_move_to_existing_path(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root() / "dst"
        session.paths.create_path(dst)

        with pytest.raises(PathExistsError):
            unwrap(session.paths.move(src, dst))

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
            unwrap(session.paths.move(src, dst))


def test_cant_move_running_sequence(session_maker, steps_configuration, time_lanes):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        unwrap(session.paths.create_path(src))

        unwrap(session.sequences.create(src, steps_configuration, time_lanes))
        unwrap(session.sequences.set_preparing(src, {}, ParameterNamespace.empty()))
        unwrap(session.sequences.set_running(src, start_time="now"))

        dst = PureSequencePath.root() / "dst"
        with pytest.raises(SequenceRunningError):
            unwrap(session.paths.move(src, dst))


def test_rename_folder(session_maker):
    with session_maker() as session:
        parent = PureSequencePath.root() / "parent"
        session.paths.create_path(parent)

        child = parent / "child"
        session.paths.create_path(child)

        new_name = PureSequencePath.root() / "new name"
        session.paths.move(parent, new_name)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(parent)
        assert session.paths.does_path_exists(new_name)
        assert session.paths.does_path_exists(new_name / "child")


def test_rename_folder_with_multiple_children(session_maker):
    with session_maker() as session:
        parent = PureSequencePath.root() / "parent"
        session.paths.create_path(parent)

        child1 = parent / "child1"
        session.paths.create_path(child1)

        child2 = parent / "child2"
        session.paths.create_path(child2)

        new_name = PureSequencePath.root() / "new name"
        session.paths.move(parent, new_name)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(parent)
        assert session.paths.does_path_exists(new_name)
        assert session.paths.does_path_exists(new_name / "child1")
        assert session.paths.does_path_exists(new_name / "child2")


def test_rename_folder_with_sibling(session_maker):
    with session_maker() as session:
        parent = PureSequencePath.root() / "parent"
        session.paths.create_path(parent)

        child = parent / "child"
        session.paths.create_path(child)

        sibling = PureSequencePath.root() / "sibling"
        session.paths.create_path(sibling)

        new_name = PureSequencePath.root() / "new name"
        session.paths.move(parent, new_name)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(parent)
        assert session.paths.does_path_exists(new_name)
        assert session.paths.does_path_exists(new_name / "child")
        assert session.paths.does_path_exists(sibling)
