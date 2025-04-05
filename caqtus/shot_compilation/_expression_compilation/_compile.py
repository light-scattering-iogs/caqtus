# pyright: strict
import contextlib
import difflib
from collections.abc import Mapping
from typing import assert_never, assert_type

import attrs
from caqtus_parsing import AST, BinaryOperator, ParseNode, UnaryOperator, parse

from caqtus.types.parameter import ParameterSchema

from ...types.recoverable_exceptions import RecoverableException
from ...types.units import Quantity, Unit
from ...types.variable_name import DottedVariableName
from ._compiled_expression import (
    CompiledExpression,
    Constant,
    ConstantParameter,
    VariableParameter,
    _CompiledExpression,
)


@attrs.frozen
class CompilationContext:
    parameter_schema: ParameterSchema
    units: Mapping[str, Unit]


def compile_expression(
    expression: str,
    compilation_context: CompilationContext,
    time_dependent: bool,
) -> CompiledExpression:
    ast = parse(str(expression))

    compiled = _compile_ast(expression, ast, compilation_context, time_dependent)
    if isinstance(compiled, CompiledExpression):
        return compiled
    else:
        assert_type(compiled, Unit)
        raise TypeError(f"Expression {expression} evaluates to a unit, not a value.")


def _compile_ast(
    expression: str,
    ast: AST,
    ctx: CompilationContext,
    time_dependent: bool,
) -> _CompiledExpression | Unit:
    match ast:
        case ParseNode.Integer(x):
            return Constant(x)
        case ParseNode.Float(x):
            return Constant(x)
        case ParseNode.Quantity(magnitude, unit_name):
            try:
                unit = ctx.units[unit_name]
            except KeyError:
                with error_context(expression, ast):
                    raise UndefinedUnitError(
                        f"Unit {unit_name} is not defined."
                    ) from None
            return Constant(Quantity(magnitude, unit))
        case ParseNode.Identifier(name):
            with error_context(expression, ast):
                return compile_identifier(DottedVariableName(name), ctx)
        case ParseNode.UnaryOperation() as unary_op:
            return compile_unary_operation(expression, unary_op, ctx, time_dependent)
        case ParseNode.BinaryOperation() as binary_op:
            return compile_binary_operation(expression, binary_op, ctx, time_dependent)
        case _:
            assert_never(ast)


def compile_identifier(
    name: DottedVariableName, ctx: CompilationContext
) -> _CompiledExpression | Unit:
    if str(name) in ctx.units:
        return ctx.units[str(name)]
    elif name in ctx.parameter_schema.constant_schema:
        parameter = ctx.parameter_schema.constant_schema[name]
        return ConstantParameter(parameter, str(name))
    elif name in ctx.parameter_schema.variable_schema:
        parameter_type = ctx.parameter_schema.variable_schema[name]
        return VariableParameter(parameter_type, str(name))
    else:
        matches = difflib.get_close_matches(
            str(name),
            {str(n) for n in ctx.parameter_schema.names()} | set(ctx.units),
            n=1,
        )
        error = UndefinedIdentifierError(f'Identifier "{name}" is not defined.')
        if matches:
            error.add_note(f'Did you mean "{matches[0]}"?')
        raise error


def compile_unary_operation(
    expression: str,
    unary_op: ParseNode.UnaryOperation,
    ctx: CompilationContext,
    time_dependent: bool,
) -> _CompiledExpression | Unit:
    operand = _compile_ast(expression, unary_op.operand, ctx, time_dependent)
    if isinstance(operand, Unit):
        with error_context(expression, unary_op):
            raise ValueError(f"Cannot apply {unary_op.operator} to {operand:~}")
    match unary_op.operator:
        case UnaryOperator.Plus:
            with error_context(expression, unary_op):
                return +operand
        case UnaryOperator.Neg:
            with error_context(expression, unary_op):
                return -operand
        case _:
            assert_never(unary_op.operator)


def compile_binary_operation(
    expression: str,
    binary_op: ParseNode.BinaryOperation,
    ctx: CompilationContext,
    time_dependent: bool,
) -> _CompiledExpression | Unit:
    lhs = _compile_ast(expression, binary_op.lhs, ctx, time_dependent)
    rhs = _compile_ast(expression, binary_op.rhs, ctx, time_dependent)
    lhs_string = expression[binary_op.lhs.span[0] : binary_op.lhs.span[1]]
    rhs_string = expression[binary_op.rhs.span[0] : binary_op.rhs.span[1]]
    match binary_op.operator:
        case BinaryOperator.Plus:
            if isinstance(lhs, Unit):
                with error_context(expression, binary_op):
                    raise TypeError(f"Cannot add unit {lhs:~} to {rhs_string}.")
            if isinstance(rhs, Unit):
                with error_context(expression, binary_op):
                    raise TypeError(f"Cannot add {lhs_string} to unit {rhs:~}.")
            with binary_context(expression, binary_op):
                return lhs + rhs
        case _:
            assert_never(binary_op.operator)


class UndefinedIdentifierError(ValueError):
    pass


class UndefinedUnitError(ValueError):
    pass


class CompilationError(RecoverableException):
    pass


@contextlib.contextmanager
def error_context(
    expr: str,
    node: AST,
):
    try:
        yield
    except Exception as e:
        underlined = (
            expr[: node.span[0]]
            + "\033[4m"
            + expr[node.span[0] : node.span[1]]
            + "\033[0m"
            + expr[node.span[1] :]
        )
        raise CompilationError(
            f'An error occurred while compiling "{underlined}"'
        ) from e


@contextlib.contextmanager
def binary_context(
    expr: str,
    binary_operation: ParseNode.BinaryOperation,
):

    try:
        yield
    except Exception as e:
        lhs = binary_operation.lhs
        rhs = binary_operation.rhs
        underlined = (
            expr[: lhs.span[0]]
            + "\033[4m"
            + expr[lhs.span[0] : lhs.span[1]]
            + "\033[24m"
            + expr[lhs.span[1] : rhs.span[0]]
            + "\033[4m"
            + expr[rhs.span[0] : rhs.span[1]]
            + "\033[24m"
            + expr[rhs.span[1] :]
        )
        raise CompilationError(
            f"An error occurred while compiling \033[1m{underlined}\033[0m"
        ) from e
