import pytest

from caqtus.shot_compilation import CompilationContext, CompilationError
from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema
from caqtus.types.units import units


def test_applying_unary_operator_to_unit_raise_error():
    expr = Expression("-MHz")

    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    expr.compile(ctx, False)
