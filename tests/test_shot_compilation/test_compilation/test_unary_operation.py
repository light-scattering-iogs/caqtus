import pytest

from caqtus.shot_compilation import CompilationContext, CompilationError
from caqtus.shot_compilation._expression_compilation import Literal
from caqtus.shot_compilation._expression_compilation._compiled_expression import (
    ConstantParameter,
    Negate,
    VariableParameter,
)
from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema
from caqtus.types.parameter._schema import QuantityType
from caqtus.types.units import Unit, units
from caqtus.types.variable_name import DottedVariableName


def test_applying_unary_operator_to_unit_raise_error():
    expr = Expression("-MHz")

    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    with pytest.raises(CompilationError):
        expr.compile(ctx, False)


def test_negating_float_returns_float():
    expr = Expression("-1.0")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(-1.0)


def test_negating_integer_returns_integer():
    expr = Expression("-1")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(-1)


def test_multiple_literal_negations_are_swallowed():
    expr = Expression("----1")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(1)


def test_negative_quantity_returns_negative_quantity():
    expr = Expression("-1.0 MHz")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(-1.0 * units["MHz"])


def test_cant_negate_boolean_constant():
    expr = Expression("-Enabled")
    ctx = CompilationContext(
        ParameterSchema(
            _constant_schema={DottedVariableName("Enabled"): True}, _variable_schema={}
        ),
        units=units,
    )
    with pytest.raises(CompilationError):
        expr.compile(ctx, False)


def test_negating_a_negation_cancels_out():
    expr = Expression("--param")
    ctx = CompilationContext(
        ParameterSchema(
            _constant_schema={DottedVariableName("param"): 1.0}, _variable_schema={}
        ),
        units=units,
    )
    assert expr.compile(ctx, False) == ConstantParameter(1.0, "param")


def test_can_negate_variable_parameter():
    expr = Expression("-param")
    parameter_type = QuantityType(Unit("MHz"))
    ctx = CompilationContext(
        ParameterSchema(
            _constant_schema={},
            _variable_schema={DottedVariableName("param"): parameter_type},
        ),
        units=units,
    )
    assert expr.compile(ctx, False) == Negate(
        VariableParameter(parameter_type, "param")
    )
