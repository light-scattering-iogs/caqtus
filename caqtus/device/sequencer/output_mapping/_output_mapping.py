import abc
from collections.abc import Mapping
from typing import Any

import attrs

import caqtus.formatter as fmt
from caqtus.types.expression import Expression
from caqtus.types.parameter import is_quantity, is_parameter, Parameter
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.types.variable_name import DottedVariableName


@attrs.define
class OutputMapping(abc.ABC):
    @abc.abstractmethod
    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> Parameter:
        raise NotImplementedError


@attrs.define
class ExpressionValue(OutputMapping):
    value: Expression = attrs.field(validator=attrs.validators.instance_of(Expression))

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> Parameter:
        evaluated = self.value.evaluate(variables)
        if not is_parameter(evaluated):
            raise InvalidTypeError(
                f"{fmt.expression(self.value)} does not evaluate to a parameter, "
                f"got {fmt.type_(type(evaluated))}.",
            )
        if is_quantity(evaluated):
            return evaluated.to_base_units()
        return evaluated
