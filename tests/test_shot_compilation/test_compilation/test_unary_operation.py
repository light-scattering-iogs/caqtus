import pytest

from caqtus.shot_compilation import CompilationContext, CompilationError
from caqtus.shot_compilation._expression_compilation import Constant
from caqtus.shot_compilation._expression_compilation._compiled_expression import (
    ConstantParameter,
    Negate,
    VariableParameter,
)
from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema
from caqtus.types.parameter._schema import Boolean, QuantityType, Integer, Float
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

    assert compiled == Constant(-1.0)


def test_negating_integer_returns_integer():
    expr = Expression("-1")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Constant(-1)


def test_multiple_literal_negations_are_swallowed():
    expr = Expression("----1")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Constant(1)


def test_negative_quantity_returns_negative_quantity():
    expr = Expression("-1.0 MHz")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Constant(-1.0 * units["MHz"])


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


def test_can_apply_pos_to_constant():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    expr = Expression("+1.0")
    assert expr.compile(ctx, False) == Constant(1.0)

    expr = Expression("+1")
    assert expr.compile(ctx, False) == Constant(1)

    expr = Expression("+10 MHz")
    assert expr.compile(ctx, False) == Constant(10 * units["MHz"])


def test_can_apply_pos_to_parameter():
    ctx = CompilationContext(
        ParameterSchema(
            _constant_schema={
                DottedVariableName("constant_int"): 1,
                DottedVariableName("constant_float"): -2.0,
                DottedVariableName("constant_quantity"): 3.0 * units["dB"],
            },
            _variable_schema={
                DottedVariableName("variable_int"): Integer(),
                DottedVariableName("variable_float"): Float(),
                DottedVariableName("variable_quantity"): QuantityType(units["MHz"]),
            },
        ),
        units=units,
    )

    assert Expression("+constant_int").compile(ctx, False) == ConstantParameter(
        1, "constant_int"
    )
    assert Expression("+constant_float").compile(ctx, False) == ConstantParameter(
        -2.0, "constant_float"
    )
    assert Expression("+constant_quantity").compile(ctx, False) == ConstantParameter(
        3.0 * units["dB"], "constant_quantity"
    )
    assert Expression("+variable_int").compile(ctx, False) == VariableParameter(
        Integer(), "variable_int"
    )
    assert Expression("+variable_float").compile(ctx, False) == VariableParameter(
        Float(), "variable_float"
    )
    assert Expression("+variable_quantity").compile(ctx, False) == VariableParameter(
        QuantityType(units["MHz"]), "variable_quantity"
    )


def test_cant_apply_pos_to_boolean_parameters():
    ctx = CompilationContext(
        ParameterSchema(
            _constant_schema={DottedVariableName("constant"): True},
            _variable_schema={DottedVariableName("variable"): Boolean()},
        ),
        units=units,
    )

    expr = Expression("+constant")
    with pytest.raises(CompilationError):
        expr.compile(ctx, False)

    expr = Expression("+variable")
    with pytest.raises(CompilationError):
        expr.compile(ctx, False)
