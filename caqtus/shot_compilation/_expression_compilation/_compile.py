from typing import assert_never, assert_type

from caqtus_parsing import AST, ParseNode, parse

from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema

from ...types.units import UNITS, Quantity, Unit
from ...types.variable_name import DottedVariableName
from ._compiled_expression import (
    BooleanLiteral,
    CompiledExpression,
    FloatLiteral,
    IntegerLiteral,
    QuantityLiteral,
)


def compile_expression(
    expression: Expression, parameter_schema: ParameterSchema, time_dependent: bool
) -> CompiledExpression:
    ast = parse(str(expression))

    compiled = _compile_ast(ast, parameter_schema, time_dependent)
    if isinstance(compiled, CompiledExpression):
        return compiled
    else:
        assert_type(compiled, Unit)
        raise TypeError(f"Expression {expression} evaluates to a unit, not a value.")


def _compile_ast(
    ast: AST, parameter_schema: ParameterSchema, time_dependent: bool
) -> CompiledExpression | Unit:
    match ast:
        case ParseNode.Integer(x):
            return IntegerLiteral(x)
        case ParseNode.Float(x):
            return FloatLiteral(x)
        case ParseNode.Quantity(magnitude, unit_name):
            unit = Unit(unit_name)
            quantity = magnitude * unit
            assert isinstance(quantity, Quantity)
            base_quantity = quantity.to_base_units()
            return QuantityLiteral(base_quantity.magnitude, base_quantity.units)
        case ParseNode.Identifier(name):
            return compile_identifier(DottedVariableName(name), parameter_schema)
        case _:
            assert_never(ast)


def compile_identifier(
    name: DottedVariableName, parameter_schema: ParameterSchema
) -> CompiledExpression | Unit:
    if str(name) in UNITS:
        return Unit(str(name))
    elif name in parameter_schema.constant_schema:
        parameter = parameter_schema.constant_schema[name]
        match parameter:
            case bool():
                return BooleanLiteral(parameter)
            case int():
                return IntegerLiteral(parameter)
            case float():
                return FloatLiteral(parameter)
            case Quantity():
                return QuantityLiteral(parameter.magnitude, parameter.unit)
            case _:
                assert_never(parameter)
    elif name in parameter_schema.variable_schema:
        parameter_type = parameter_schema.variable_schema[name]
        raise NotImplementedError

    else:
        raise ValueError(f"Parameter <{name}> is not defined.")
