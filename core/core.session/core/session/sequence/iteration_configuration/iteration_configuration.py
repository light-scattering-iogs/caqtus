import abc
from typing import Optional


class IterationConfiguration(abc.ABC):
    """Defines how parameters should be iterated over for a sequence.

    This is an abstract base class that defines the interface for iterations.
    It is meant to be subclassed to define different types of iterations.
    """

    @abc.abstractmethod
    def expected_number_shots(self) -> Optional[int]:
        """Return the expected number of shots defined by this iteration.

        If the number of shots can be determined ahead of time, this method should
        return that number.
        If the number of shots cannot be determined ahead of time, this method should
        return None.
        In doubt, the method should return None and not a wrong guess.
        """

        raise NotImplementedError
