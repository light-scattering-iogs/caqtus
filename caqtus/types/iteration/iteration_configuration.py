from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import TypeGuard

from ..parameter import Parameter, ParameterSchema
from ..variable_name import DottedVariableName


class IterationConfiguration(abc.ABC):
    """Defines how parameters should be iterated over.

    This is an abstract base class that defines the interface for iterations of shots
    during a sequence.
    It is meant to be subclassed to define different types of iterations.
    """

    @abc.abstractmethod
    def expected_number_shots(self) -> int | Unknown:
        """Return the expected number of shots defined by this iteration.

        If the number of shots can be statically determined ahead of time, this method
        should return that number.
        If the number of shots cannot be determined ahead of time, this method should
        return unknown.
        In doubt, the method must return unknown and not a possibly wrong guess.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_parameter_names(self) -> set[DottedVariableName]:
        """Return the names of the parameters that are iterated over.

        This method must return the name of the parameters whose values are changed
        during the iteration.
        The iteration must set the values of all these parameters before each shot.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_parameter_schema(
        self, initial_parameters: Mapping[DottedVariableName, Parameter]
    ) -> ParameterSchema:
        """Compute the schema of the parameters that are iterated over.

        Args:
            initial_parameters: The values of the parameters that are defined before the
                iteration starts.
                Unless the iteration overwrites the values of these parameters, they
                are considered constant during the iteration.

        Returns:
            The schema of the parameters that are iterated over.

            Implementations of this method should infer the types of the parameters
            correctly as the consumers of this method rely on the correctness of the
            inferred types.
        """

        raise NotImplementedError


class Unknown:
    """Instances of this class represent an unknown positive integer.

    It can be added or multiplied with a positive integer.
    It is absorbent for addition and for multiplication with a non-zero operand.
    Multiplication by zero return zero.
    """

    def __add__(self, other):
        match other:
            case int(x) if x >= 0:
                return self
            case Unknown():
                return self
            case _:
                return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __mul__(self, other):
        match other:
            case 0:
                return 0
            case Unknown():
                return self
            case int(x) if x > 0:
                return self
            case _:
                return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __repr__(self):
        return "Unknown()"

    def __str__(self):
        return "unknown"


def is_unknown(value) -> TypeGuard[Unknown]:
    return isinstance(value, Unknown)
