import pytest

from caqtus.session import SequenceNotCrashedError, TracebackSummary
from caqtus.types.parameter import ParameterNamespace
from caqtus.utils.result import unwrap


def test_get_exception_not_crashed(session_maker, draft_sequence):
    with session_maker.session() as session:
        with pytest.raises(SequenceNotCrashedError):
            unwrap(session.sequences.get_exception(draft_sequence))


def test_get_exception_crashed(session_maker, crashed_sequence):
    with session_maker.session() as session:
        assert unwrap(
            session.sequences.get_exception(crashed_sequence)
        ) == TracebackSummary.from_exception(RuntimeError("error"))


def test_set_exception_after_reset(session_maker, crashed_sequence):
    with session_maker.session() as session:
        unwrap(session.sequences.reset_to_draft(crashed_sequence))
        unwrap(
            session.sequences.set_preparing(
                crashed_sequence, {}, ParameterNamespace.empty()
            )
        )
        unwrap(session.sequences.set_running(crashed_sequence, start_time="now"))
        tb_1 = TracebackSummary.from_exception(ValueError("error 1"))
        unwrap(session.sequences.set_crashed(crashed_sequence, tb_1, stop_time="now"))
        assert unwrap(session.sequences.get_exception(crashed_sequence)) == tb_1
