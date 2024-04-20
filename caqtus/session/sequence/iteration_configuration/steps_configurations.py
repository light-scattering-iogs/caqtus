from __future__ import annotations

import functools
from collections.abc import Mapping
from typing import TypeAlias, TypeGuard, assert_never, Any

import attrs

from caqtus.types.expression import Expression
from caqtus.types.parameter import AnalogValue, is_analog_value, NotAnalogValueError
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from . import Unknown
from .iteration_configuration import IterationConfiguration


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
    __match_args__ = ("variable", "start", "stop", "num", "sub_steps")
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
        return (
            f"for {self.variable} = {self.start} to {self.stop} with {self.num} steps"
        )


@attrs.define
class ArangeLoop(ContainsSubSteps):
    __match_args__ = ("variable", "start", "stop", "step", "sub_steps")
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
        return (
            f"for {self.variable} = {self.start} to {self.stop} with {self.step} "
            f"spacing"
        )


@attrs.define
class ExecuteShot:
    pass


def unstructure_hook(execute_shot: ExecuteShot) -> str:
    return {"execute": "shot"}


def structure_hook(data: str, cls: type[ExecuteShot]) -> ExecuteShot:
    return ExecuteShot()


serialization.register_unstructure_hook(ExecuteShot, unstructure_hook)

serialization.register_structure_hook(ExecuteShot, structure_hook)


Step: TypeAlias = ExecuteShot | VariableDeclaration | LinspaceLoop | ArangeLoop


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


@attrs.define
class StepsConfiguration(IterationConfiguration):
    steps: list[Step] = attrs.field(
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=validate_step,
        ),
        on_setattr=attrs.setters.validate,
    )

    def expected_number_shots(self) -> int | Unknown:
        return sum(expected_number_shots(step) for step in self.steps)

    def get_parameter_names(self) -> set[DottedVariableName]:
        return set().union(*[get_parameter_names(step) for step in self.steps])

    @classmethod
    def dump(cls, steps_configuration: StepsConfiguration) -> serialization.JSON:
        return serialization.unstructure(steps_configuration, StepsConfiguration)

    @classmethod
    def load(cls, data: serialization.JSON) -> StepsConfiguration:
        return serialization.structure(data, StepsConfiguration)


@functools.singledispatch
def expected_number_shots(step: Step) -> int | Unknown:  # type: ignore
    assert_never(step)


@expected_number_shots.register
def _(step: VariableDeclaration):
    return 0


@expected_number_shots.register
def _(step: ExecuteShot):
    return 1


@expected_number_shots.register
def _(step: LinspaceLoop):
    sub_steps_number = sum(
        expected_number_shots(sub_step) for sub_step in step.sub_steps
    )
    return sub_steps_number * step.num


@expected_number_shots.register
def _(step: ArangeLoop):
    # We need to be careful to not return a wrong number of shots.
    # In particular, we return unknown if the number of shots for the step depends on
    # a variable.
    return Unknown()


def get_parameter_names(step: Step) -> set[DottedVariableName]:
    match step:
        case VariableDeclaration(variable=variable, value=_):
            return {variable}
        case ExecuteShot():
            return set()
        case ContainsSubSteps(sub_steps=sub_steps):
            return set().union(
                *[get_parameter_names(sub_step) for sub_step in sub_steps]
            )
        case _:
            assert_never(step)


def evaluate_arange_loop_parameters(
    arange_loop: ArangeLoop,
    variables: Mapping[DottedVariableName, Any],
) -> tuple[AnalogValue, AnalogValue, AnalogValue]:
    """Evaluates the start, stop and step values of an arange loop.

    Raises:
        EvaluationError: if one value could not be evaluated.
        NotAnalogValueError: if one evaluated value is not an analog value.
    """

    start = arange_loop.start.evaluate(variables)
    if not is_analog_value(start):
        raise NotAnalogValueError(
            f"Start of loop '{arange_loop}' is not an analog value."
        )
    stop = arange_loop.stop.evaluate(variables)
    if not is_analog_value(stop):
        raise NotAnalogValueError(
            f"Stop of loop '{arange_loop}' is not an analog value."
        )
    step = arange_loop.step.evaluate(variables)
    if not is_analog_value(step):
        raise NotAnalogValueError(
            f"Step of loop '{arange_loop}' is not an analog value."
        )
    return start, stop, step
