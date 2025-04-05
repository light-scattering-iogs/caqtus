import contextlib
import difflib
from typing import Self, assert_never, assert_type

from caqtus_parsing import AST, ParseNode, parse

from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema

from ...types.recoverable_exceptions import RecoverableException
from ...types.units import UNITS, Quantity, Unit, units
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

    compiled = _compile_ast(expression, ast, parameter_schema, time_dependent)
    if isinstance(compiled, CompiledExpression):
        return compiled
    else:
        assert_type(compiled, Unit)
        raise TypeError(f"Expression {expression} evaluates to a unit, not a value.")


def _compile_ast(
    expression: Expression,
    ast: AST,
    parameter_schema: ParameterSchema,
    time_dependent: bool,
) -> CompiledExpression | Unit:
    match ast:
        case ParseNode.Integer(x):
            return IntegerLiteral(x)
        case ParseNode.Float(x):
            return FloatLiteral(x)
        case ParseNode.Quantity(magnitude, unit_name):
            try:
                unit = units[unit_name]
            except KeyError:
                with compilation_context(expression, ast):
                    raise UndefinedUnitError(
                        f"Unit {unit_name} is not defined."
                    ) from None
            quantity = magnitude * unit
            assert isinstance(quantity, Quantity)
            base_quantity = quantity.to_base_units()
            return QuantityLiteral(base_quantity.magnitude, base_quantity.units)
        case ParseNode.Identifier(name):
            with compilation_context(expression, ast):
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
        matches = difflib.get_close_matches(
            str(name), [str(n) for n in parameter_schema.names()], n=1
        )
        error = UndefinedParameterError(f'Parameter "{name}" is not defined.')
        if matches:
            error.add_note(f'Did you mean "{matches[0]}"?')
        raise error


class UndefinedParameterError(ValueError):
    pass


class UndefinedUnitError(ValueError):
    pass


class CompilationError(RecoverableException):
    @classmethod
    def new(cls, expression: Expression, node: AST) -> Self:
        expr = str(expression)
        underlined = (
            expr[: node.span[0]]
            + "\033[4m"
            + expr[node.span[0] : node.span[1]]
            + "\033[0m"
            + expr[node.span[1] :]
        )
        return cls(f'An error occurred while compiling "{underlined}".')


@contextlib.contextmanager
def compilation_context(
    expression: Expression,
    ast: AST,
):
    try:
        yield
    except Exception as e:
        raise CompilationError.new(expression, ast) from e
