from typing import Never

import attrs


@attrs.frozen
class _Success[T]:
    value: T

    def unwrap(self) -> T:
        return self.value


@attrs.frozen
class _Failure[E: Exception]:
    error: E

    def unwrap(self) -> Never:
        raise self.error


type _Result[T, E: Exception] = _Success[T] | _Failure[E]
