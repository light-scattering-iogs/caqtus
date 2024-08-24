import pytest

from caqtus.session import SequenceNotCrashedError, TracebackSummary, State
from caqtus.session._return_or_raise import unwrap


def test_get_exception_not_crashed(session_maker, draft_sequence):
    with session_maker.session() as session:
        with pytest.raises(SequenceNotCrashedError):
            unwrap(session.sequences.get_exception(draft_sequence))


def test_get_exception_crashed(session_maker, crashed_sequence):
    with session_maker.session() as session:
        assert unwrap(session.sequences.get_exception(crashed_sequence)) is None


def test_set_exception_crashed(session_maker, crashed_sequence):
    error = RuntimeError("error")

    tb = TracebackSummary.from_exception(error)
    with session_maker.session() as session:
        unwrap(session.sequences.set_exception(crashed_sequence, tb))
    with session_maker.session() as session:
        assert unwrap(session.sequences.get_exception(crashed_sequence)) == tb


def test_set_exception_after_reset(session_maker, crashed_sequence):
    error = RuntimeError("error")

    tb = TracebackSummary.from_exception(error)
    with session_maker.session() as session:
        unwrap(session.sequences.set_exception(crashed_sequence, tb))

    with session_maker.session() as session:
        session.sequences.set_state(crashed_sequence, State.DRAFT)
        session.sequences.set_state(crashed_sequence, State.PREPARING)
        session.sequences.set_state(crashed_sequence, State.RUNNING)
        session.sequences.set_state(crashed_sequence, State.CRASHED)

    with session_maker.session() as session:
        assert unwrap(session.sequences.get_exception(crashed_sequence)) is None
        unwrap(session.sequences.set_exception(crashed_sequence, tb))
