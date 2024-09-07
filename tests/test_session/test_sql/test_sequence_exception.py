import pytest

from caqtus.session import SequenceNotCrashedError, TracebackSummary, State


def test_get_exception_not_crashed(session_maker, draft_sequence):
    with session_maker.session() as session:
        with pytest.raises(SequenceNotCrashedError):
            session.sequences.get_exception(draft_sequence).unwrap()


def test_get_exception_crashed(session_maker, crashed_sequence):
    with session_maker.session() as session:
        assert session.sequences.get_exception(crashed_sequence).unwrap() is None


def test_set_exception_crashed(session_maker, crashed_sequence):
    error = RuntimeError("error")

    tb = TracebackSummary.from_exception(error)
    with session_maker.session() as session:
        session.sequences.set_exception(crashed_sequence, tb).unwrap()
    with session_maker.session() as session:
        assert session.sequences.get_exception(crashed_sequence).unwrap() == tb


def test_set_exception_after_reset(session_maker, crashed_sequence):
    error = RuntimeError("error")

    tb = TracebackSummary.from_exception(error)
    with session_maker.session() as session:
        session.sequences.set_exception(crashed_sequence, tb).unwrap()

    with session_maker.session() as session:
        session.sequences.set_state(crashed_sequence, State.DRAFT)
        session.sequences.set_state(crashed_sequence, State.PREPARING)
        session.sequences.set_state(crashed_sequence, State.RUNNING)
        session.sequences.set_state(crashed_sequence, State.CRASHED)

    with session_maker.session() as session:
        assert session.sequences.get_exception(crashed_sequence).unwrap() is None
        session.sequences.set_exception(crashed_sequence, tb).unwrap()
