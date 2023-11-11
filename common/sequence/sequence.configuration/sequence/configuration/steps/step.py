from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Optional, Self

from anytree import NodeMixin

from util import attrs


@attrs.define
class Step(NodeMixin, ABC):
    def __init__(
        self, parent: Optional[Self] = None, children: Optional[Iterable[Self]] = None
    ):
        self.parent = parent
        if children is not None:
            self.children = list(children)

    def row(self):
        if self.is_root:
            return 0
        else:
            for i, child in enumerate(self.parent.children):
                if child is self:
                    return i

    @abstractmethod
    def expected_number_shots(self) -> Optional[int]:
        """Return the number of shots planned inside this step

        Returns None if this is unknown.
        """
        raise NotImplementedError()

    @abstractmethod
    def __eq__(self, other):
        raise NotImplementedError()


def compute_total_number_shots(steps: Iterable[Step]) -> Optional[int]:
    result = 0
    for step in steps:
        step_result = step.expected_number_shots()
        if step_result is None:
            return None
        result += step_result
    return result
