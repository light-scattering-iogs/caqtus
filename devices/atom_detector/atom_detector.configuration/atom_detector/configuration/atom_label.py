from collections.abc import Hashable
from typing import Protocol, runtime_checkable


@runtime_checkable
class AtomLabel(Hashable, Protocol):
    def __str__(self) -> str:
        ...
