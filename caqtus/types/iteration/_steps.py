from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, TypeGuard, assert_never, assert_type

import attrs
import numpy

import caqtus.formatter as fmt
from caqtus.types.expression import Expression
from caqtus.types.parameter import (
    NotAnalogValueError,
)

from ..parameter._analog_value import ScalarAnalogValue, is_scalar_analog_value
from ..units import (
    DimensionalityError,
    InvalidDimensionalityError,
    Quantity,
    Unit,
    dimensionless,
)
from ..variable_name import DottedVariableName
from ._user_input_steps import UserInputStep

type Step = (
    ExecuteShot | VariableDeclaration | LinspaceLoop | ArangeLoop | UserInputStep
)
"""Type alias for the different types of steps."""


def validate_step(instance, attribute, step):
    if is_step(step):
        return
    else:
        raise TypeError(f"Invalid step: {step}")


@attrs.define
class ContainsSubSteps:
    sub_steps: list[Step] = attrs.field(
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=validate_step,
        ),
        on_setattr=attrs.setters.validate,
    )


@attrs.define
class VariableDeclaration:
    """Represents the declaration of a variable.

    Attributes:
        variable: The name of the variable.
        value: The unevaluated to assign to the variable.
    """

    __match_args__ = ("variable", "value")

    variable: DottedVariableName = attrs.field(
        validator=attrs.validators.instance_of(DottedVariableName),
        on_setattr=attrs.setters.validate,
    )
    value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.variable} = {self.value}"


@attrs.define
class LinspaceLoop(ContainsSubSteps):
    """Represents a loop that iterates between two values with a fixed number of steps.

    Attributes:
        variable: The name of the variable that is being iterated over.
        start: The start value of the variable.
        stop: The stop value of the variable.
        num: The number of steps to take between the start and stop values.
    """

    __match_args__ = (
        "variable",  # pyright: ignore[reportAssignmentType]
        "start",
        "stop",
        "num",
        "sub_steps",
    )
    variable: DottedVariableName = attrs.field(
        validator=attrs.validators.instance_of(DottedVariableName),
        on_setattr=attrs.setters.validate,
    )
    start: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    stop: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    num: int = attrs.field(
        converter=int,
        validator=attrs.validators.ge(0),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    def __str__(self):
        return f"linspace loop over {self.variable}"

    def loop_values(
        self, evaluation_context: Mapping[DottedVariableName, Any]
    ) -> Iterator[ScalarAnalogValue]:
        """Returns the values that the variable represented by this loop takes.

        Args:
            evaluation_context: Contains the value of the variables with which to
                evaluate the start and stop expressions of the loop.

        Raises:
            EvaluationError: if the start or stop expressions could not be evaluated.
            NotAnalogValueError: if the start or stop expressions don't evaluate to an
                analog value.
            DimensionalityError: if the start or stop values are not commensurate.
        """

        try:
            start = _to_scalar_analog_value(self.start.evaluate(evaluation_context))
        except NotAnalogValueError:
            raise NotAnalogValueError(
                f"Start {fmt.expression(self.start)} of {self} does not evaluate to an "
                f"analog value"
            ) from None
        try:
            stop = _to_scalar_analog_value(self.stop.evaluate(evaluation_context))
        except NotAnalogValueError:
            raise NotAnalogValueError(
                f"Stop {fmt.expression(self.stop)} of {self} does not evaluate to an "
                f"analog value"
            ) from None

        # Here we enforce that the values generated have the same format as the start
        # value.
        if isinstance(start, float):
            try:
                stop = _to_dimensionless_float(stop)
            except DimensionalityError:
                raise InvalidDimensionalityError(
                    f"Start {fmt.expression(self.start)} of {self} is "
                    f"dimensionless, but stop {fmt.expression(self.stop)} cannot "
                    f"be converted to dimensionless"
                ) from None
            assert_type(stop, float)
            assert_type(start, float)
            for value in numpy.linspace(start, stop, self.num):
                yield float(value.item())
        elif isinstance(start, int):
            raise AssertionError("start must be strictly a float or a Quantity")
        else:
            try:
                stop = _to_unit(stop, start.units)
            except DimensionalityError as e:
                raise InvalidDimensionalityError(
                    f"Start {fmt.expression(self.start)} of {self} has invalid "
                    f"dimensionality."
                ) from e
            assert_type(start, Quantity[float])
            assert_type(stop, Quantity[float])
            for value in numpy.linspace(start.magnitude, stop.magnitude, self.num):
                yield Quantity(float(value), start.units)


@attrs.define
class ArangeLoop(ContainsSubSteps):
    """Represents a loop that iterates between two values with a fixed step size.

    Attributes:
        variable: The name of the variable that is being iterated over.
        start: The start value of the variable.
        stop: The stop value of the variable.
        step: The step size between each value.
    """

    __match_args__ = (
        "variable",  # pyright: ignore[reportAssignmentType]
        "start",
        "stop",
        "step",
        "sub_steps",
    )
    variable: DottedVariableName = attrs.field(
        validator=attrs.validators.instance_of(DottedVariableName),
        on_setattr=attrs.setters.validate,
    )
    start: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    stop: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )
    step: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"arange loop over {fmt.shot_param(self.variable)}"

    def loop_values(
        self, evaluation_context: Mapping[DottedVariableName, Any]
    ) -> Iterator[ScalarAnalogValue]:
        """Returns the values that the variable represented by this loop takes.

        Args:
            evaluation_context: Contains the value of the variables with which to
                evaluate the start, stop and step expressions of the loop.

        Raises:
            EvaluationError: if the start, stop or step expressions could not be
                evaluated.
            NotAnalogValueError: if the start, stop or step expressions don't evaluate
                to an analog value.
            InvalidDimensionalityError: if the start, stop and step values are not
                commensurate.
        """

        try:
            start = _to_scalar_analog_value(self.start.evaluate(evaluation_context))
        except NotAnalogValueError:
            raise NotAnalogValueError(
                f"Start {fmt.expression(self.start)} of {self} does not evaluate to an "
                f"analog value"
            ) from None
        try:
            stop = _to_scalar_analog_value(self.stop.evaluate(evaluation_context))
        except NotAnalogValueError:
            raise NotAnalogValueError(
                f"Stop {fmt.expression(self.stop)} of {self} does not evaluate to an "
                f"analog value"
            ) from None
        try:
            step = _to_scalar_analog_value(self.step.evaluate(evaluation_context))
        except NotAnalogValueError:
            raise NotAnalogValueError(
                f"Step {fmt.expression(self.step)} of {self} does not evaluate to an "
                f"analog value"
            ) from None

        # Here we enforce that the values generated have the same format as the start
        # value.
        if isinstance(start, float):
            try:
                stop = _to_dimensionless_float(stop)
            except DimensionalityError:
                raise InvalidDimensionalityError(
                    f"Start {fmt.expression(self.start)} of {self} is "
                    f"dimensionless, but stop {fmt.expression(self.stop)} cannot "
                    f"be converted to dimensionless"
                ) from None
            try:
                step = _to_dimensionless_float(step)
            except DimensionalityError:
                raise InvalidDimensionalityError(
                    f"Step {fmt.expression(self.step)} of {self} is "
                    f"dimensionless, but stop {fmt.expression(self.stop)} cannot "
                    f"be converted to dimensionless"
                ) from None
            assert_type(start, float)
            assert_type(stop, float)
            assert_type(step, float)
            for value in numpy.arange(start, stop, step):
                yield float(value)
        elif isinstance(start, int):
            raise AssertionError("start must be strictly a float or a Quantity")
        else:
            try:
                stop = _to_unit(stop, start.units)
            except DimensionalityError as e:
                raise InvalidDimensionalityError(
                    f"Start {fmt.expression(self.start)} of {self} has invalid "
                    f"dimensionality."
                ) from e
            try:
                step = _to_unit(step, start.units)
            except DimensionalityError as e:
                raise InvalidDimensionalityError(
                    f"Step {fmt.expression(self.step)} of {self} has invalid "
                    f"dimensionality."
                ) from e
            assert_type(start, Quantity[float])
            assert_type(stop, Quantity[float])
            assert_type(step, Quantity[float])
            for value in numpy.arange(start.magnitude, stop.magnitude, step.magnitude):
                yield Quantity(float(value), start.units)


@attrs.define
class ExecuteShot:
    """Step that represents the execution of a shot."""

    def __str__(self):
        return "do shot"


def is_step(step) -> TypeGuard[Step]:
    return isinstance(
        step,
        (
            ExecuteShot,
            VariableDeclaration,
            LinspaceLoop,
            ArangeLoop,
        ),
    )


def _to_scalar_analog_value(value: Any) -> ScalarAnalogValue:
    """Attempt to convert a value to a scalar analog value.

    Raises:
        NotAnalogValueError: If the value can't be converted to a scalar analog value.
    """

    if isinstance(value, int):
        return float(value)
    if not is_scalar_analog_value(value):
        raise NotAnalogValueError(value)
    return value


def _to_dimensionless_float(value: ScalarAnalogValue) -> float:
    """Convert a scalar analog value to a dimensionless float.

    Raises:
        DimensionalityError: If the value is a quantity not commensurate with
        dimensionless.
    """

    if isinstance(value, Quantity):
        return value.to_unit(dimensionless).magnitude
    elif isinstance(value, float):
        return value
    elif isinstance(value, int):
        raise AssertionError("stop must be strictly a float or a Quantity")
    else:
        assert_never(value)


def _to_unit[U: Unit](value: ScalarAnalogValue, unit: U) -> Quantity[float, U]:
    """Convert a scalar analog value to the same unit as another.

    Raises:
        DimensionalityError: If the value is a quantity not commensurate with the unit.
    """

    if isinstance(value, float):
        value = Quantity(value, dimensionless)
    elif isinstance(value, int):
        raise AssertionError("stop must be strictly a float or a Quantity")
    return value.to_unit(unit)
