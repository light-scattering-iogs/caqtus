from typing import Any, assert_never

from caqtus_parsing import (
    AST,
    BinaryOperation,
    BinaryOperator,
    Call,
    Float,
    Identifier,
    Integer,
    UnaryOperation,
    UnaryOperator,
    parse,
)
from caqtus_parsing import Quantity as QuantityNode
from typing_extensions import TypeIs

import caqtus.formatter as fmt
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameters
from caqtus.types.recoverable_exceptions import EvaluationError, InvalidTypeError
from caqtus.types.units import DimensionalityError, Quantity, Unit, is_scalar_quantity

from ._constants import CONSTANTS
from ._exceptions import (
    InvalidOperationError,
    UndefinedParameterError,
)
from ._functions import SCALAR_FUNCTIONS
from ._scalar import Scalar


def evaluate_scalar_expression(
    expression: Expression, parameters: Parameters
) -> Scalar:
    """Evaluate a scalar expression.

    Args:
        expression: The expression to evaluate.
        parameters: The parameters to use in the evaluation.

    Returns:
        The result of the evaluation.

    Raises:
        EvaluationError: if an error occurred during evaluation, with the reason for the
            error as the exception cause.
    """

    try:
        ast = parse(str(expression))
        return evaluate_expression(ast, parameters)
    except (EvaluationError, InvalidSyntaxError) as error:
        raise EvaluationError(
            f"Could not evaluate {fmt.expression(expression)}."
        ) from error


def evaluate_bool_expression(expression: AST, parameters: Parameters) -> bool:
    value = evaluate_expression(expression, parameters)
    if not isinstance(value, bool):
        raise InvalidTypeError(
            f"Expected {fmt.expression(expression)} to evaluate to a boolean, "
            f"but got {fmt.type_(type(value))}."
        )
    return value


def evaluate_float_expression(expression: AST, parameters: Parameters) -> float:
    value = evaluate_expression(expression, parameters)
    try:
        return float(value)
    except DimensionalityError as error:
        raise InvalidOperationError(
            f"Could not convert {fmt.expression(expression)} to a float."
        ) from error


def evaluate_expression(expression: AST, parameters: Parameters) -> Scalar:
    match expression:
        case Integer(value) | Float(value):
            return value
        case Identifier(name):
            return evaluate_scalar_variable(name, parameters)
        case BinaryOperation() as binary_operation:
            return evaluate_binary_operator(binary_operation, parameters)
        case UnaryOperation() as unary_operator:
            return evaluate_unary_operator(unary_operator, parameters)
        case QuantityNode():
            return evaluate_quantity(expression)
        case Call():
            return evaluate_function_call(expression, parameters)
        case _:  # pragma: no cover
            assert_never(expression)


def evaluate_scalar_variable(name: str, parameters: Parameters) -> Scalar:
    if name in parameters:
        # We can use str as key instead of DottedVariableName because they have the
        # same hash.
        return parameters[name]  # type: ignore[reportArgumentType]
    elif name in CONSTANTS:
        return CONSTANTS[name]
    else:
        raise UndefinedParameterError(f"Parameter {name} is not defined.")


def evaluate_function_call(
    function_call: Call,
    parameters: Parameters,
) -> Scalar:
    function_name = function_call.name
    try:
        # We can use str as key instead of VariableName because they have the
        # same hash.
        function = SCALAR_FUNCTIONS[function_name]  # type: ignore[reportArgumentType]
    except KeyError:
        raise UndefinedFunctionError(
            f"Function {function_name} is not defined."
        ) from None
    arguments = [
        evaluate_expression(argument, parameters) for argument in function_call.args
    ]
    return function(*arguments)


def evaluate_binary_operator(
    binary_operation: BinaryOperation,
    parameters: Parameters,
) -> Scalar:
    left = evaluate_expression(binary_operation.lhs, parameters)
    right = evaluate_expression(binary_operation.rhs, parameters)
    match binary_operation.operator:
        case BinaryOperator.Plus:
            result = left + right
        case BinaryOperator.Minus:
            result = left - right
        case BinaryOperator.Times:
            result = left * right
        case BinaryOperator.Div:
            result = left / right
        case BinaryOperator.Pow:
            if not isinstance(right, (int, float)):
                raise InvalidOperationError(
                    f"The exponent {binary_operation.rhs} must be a real number, not "
                    f"{right}."
                )
            result = left**right
        case _:  # pragma: no cover
            assert_never(binary_operation.operator)
    assert is_scalar(result)
    return result


def evaluate_unary_operator(
    unary_operation: UnaryOperation,
    parameters: Parameters,
) -> Scalar:
    operand = evaluate_expression(unary_operation.operand, parameters)
    match unary_operation.operator:
        case UnaryOperator.Neg:
            result = -operand
        case _:  # pragma: no cover
            assert_never(unary_operation.operator)
    assert is_scalar(result)
    return result


def evaluate_quantity(quantity: QuantityNode) -> Quantity[float]:
    return Quantity(quantity.value, Unit(quantity.unit))


def is_scalar(value: Any) -> TypeIs[Scalar]:
    return isinstance(value, (int, bool, float)) or is_scalar_quantity(value)


class UndefinedFunctionError(EvaluationError):
    pass
