import datetime
from typing import Protocol, Optional

from caqtus.session import Sequence, PureSequencePath


class SequenceFunction[T](Protocol):
    def __call__(self, sequence: Sequence) -> T: ...


# noinspection PyPep8Naming
class cache_per_sequence[T]:  # noqa: N801
    def __init__(self, func: SequenceFunction[T]) -> None:
        self.func = func
        self.cache: dict[PureSequencePath, tuple[Optional[datetime.datetime], T]] = {}

    def __call__(self, sequence: Sequence) -> T:
        path = sequence.path
        last_start_time = sequence.get_start_time()
        if path not in self.cache:
            result = self.func(sequence)
            self.cache[path] = (last_start_time, result)
            return result
        else:
            cached_start_time, result = self.cache[path]
            sequence_has_been_started = last_start_time is not None
            sequence_has_been_reset = last_start_time != cached_start_time
            if sequence_has_been_reset or not sequence_has_been_started:
                result = self.func(sequence)
                self.cache[path] = (last_start_time, result)
                return result
            else:
                return result
