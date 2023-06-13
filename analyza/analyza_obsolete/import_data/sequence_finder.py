from collections.abc import Mapping
from typing import Optional

from experiment.session import (
    ExperimentSessionMaker,
    get_standard_experiment_session_maker,
)
from sequence.runtime import Sequence


class SequenceMapping(Mapping[str, Sequence]):
    """Allows to access a sequence by its path.

    The main purpose of this class is to provide tab completion for sequence paths when using IPython.

    Example:
        >>> sequences = SequenceMapping()
        >>> sequence = sequences["path.to.sequence"]
    """

    def __init__(self, session_maker: Optional[ExperimentSessionMaker] = None):
        if session_maker is None:
            session_maker = get_standard_experiment_session_maker()
        self._session = session_maker()

    def __len__(self) -> int:
        with self._session.activate():
            return len(Sequence.get_all_sequence_names(self._session))

    def __iter__(self):
        with self._session.activate():
            return iter(Sequence.get_all_sequence_names(self._session))

    def _ipython_key_completions_(self):
        with self._session.activate():
            return Sequence.get_all_sequence_names(self._session)

    def __getitem__(self, sequence_path: str) -> Sequence:
        sequence = Sequence(sequence_path)
        with self._session.activate():
            if sequence.exists(self._session):
                return sequence
        raise KeyError(f"Sequence {sequence_path} does not exist")


sequences = SequenceMapping()
