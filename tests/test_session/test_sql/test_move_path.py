from caqtus.session import PureSequencePath


def test_move_single_node(session_maker):
    with session_maker() as session:
        src = PureSequencePath.root() / "src"
        session.paths.create_path(src)
        dst = PureSequencePath.root() / "dst"

        session.paths.move(src, dst)

        session.paths.check_valid()

        assert not session.paths.does_path_exists(src)
        assert session.paths.does_path_exists(dst)
