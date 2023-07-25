from collections.abc import Hashable
from typing import Protocol


class AtomLabel(Hashable, Protocol):
    def __str__(self) -> str:
        ...
