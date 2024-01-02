import abc
from typing import Optional


class IterationConfiguration(abc.ABC):
    @abc.abstractmethod
    def expected_number_shots(self) -> Optional[int]:
        raise NotImplementedError
