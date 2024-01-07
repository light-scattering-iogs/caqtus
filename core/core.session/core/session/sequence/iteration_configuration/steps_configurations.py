from __future__ import annotations

from typing import Optional, TypeAlias, TypeGuard, assert_never

import attrs

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from util import serialization
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


@attrs.define
class ImportConstantTable:
    table: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    alias: Optional[str] = attrs.field(
        converter=attrs.converters.optional(str), on_setattr=attrs.setters.convert
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


Step: TypeAlias = (
    ExecuteShot | VariableDeclaration | LinspaceLoop | ArangeLoop | ImportConstantTable
)


def is_step(step) -> TypeGuard[Step]:
    return isinstance(
        step,
        (
            ExecuteShot,
            VariableDeclaration,
            LinspaceLoop,
            ArangeLoop,
            ImportConstantTable,
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

    def expected_number_shots(self) -> Optional[int]:
        child_number_shots = [expected_number_shots(step) for step in self.steps]
        if any(child_number_shots is None):
            return None
        return sum(child_number_shots)

    @classmethod
    def dump(cls, steps_configuration: StepsConfiguration) -> serialization.JSON:
        return serialization.unstructure(steps_configuration, StepsConfiguration)

    @classmethod
    def load(cls, data: serialization.JSON) -> StepsConfiguration:
        return serialization.structure(data, StepsConfiguration)


def expected_number_shots(step: Step) -> Optional[int]:
    match step:
        case VariableDeclaration():
            return 0
        case ExecuteShot():
            return 1
        case LinspaceLoop(_, _, _, num, sub_steps):
            return None
        case ArangeLoop(_, _, _, _, sub_steps):
            return None
        case ImportConstantTable():
            return 0
        case _:
            assert_never(step)
