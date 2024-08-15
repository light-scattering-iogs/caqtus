import ast
import re
from collections.abc import Mapping
from functools import cached_property
from typing import Optional, Any

import numpy
import token_utils

from caqtus.utils import serialization
from ..recoverable_exceptions import EvaluationError
from ..units import units
from ..variable_name import DottedVariableName, VariableName

EXPRESSION_REGEX = re.compile(".*")


def square_wave(t, period, duty_cycle=0.5, low=0, high=1):
    x = t / period
    x = x - numpy.floor(x)
    is_high = x < duty_cycle
    result = numpy.where(is_high, high, low)
    return result


#: Built-in functions and constants available in expressions.
BUILTINS: Mapping[str, Any] = {
    "abs": numpy.abs,
    "arccos": numpy.arccos,
    "arcsin": numpy.arcsin,
    "arctan": numpy.arctan,
    "arctan2": numpy.arctan2,
    "ceil": numpy.ceil,
    "cos": numpy.cos,
    "cosh": numpy.cosh,
    "degrees": numpy.degrees,
    "e": numpy.e,
    "exp": numpy.exp,
    "floor": numpy.floor,
    "log": numpy.log,
    "log10": numpy.log10,
    "log2": numpy.log2,
    "pi": numpy.pi,
    "radians": numpy.radians,
    "sin": numpy.sin,
    "sinh": numpy.sinh,
    "sqrt": numpy.sqrt,
    "tan": numpy.tan,
    "tanh": numpy.tanh,
    "square_wave": square_wave,
    "max": max,
    "min": min,
    "Enabled": True,
    "Disabled": False,
} | {str(name): value for name, value in units.items()}


class Expression:
    """Represents a mathematical expression that can be evaluated in a given context.

    This class is a wrapper around a python string expression that can be evaluated
    later when the values of the variables it depends on are known.

    The expression is immutable.

    If the expression contains syntax errors, they only will be raised when the
    expression is evaluated.

    The expression must be a valid python expression, with some exceptions:
    * The % symbol is understood as a multiplication by 0.01.
    * The ° symbol is understood as the degree symbol and will be replaced by the
        name `deg` in the expression.
    * Implicit multiplication is allowed, so that 'a b' will be parsed as 'a * b'.
    """

    def __init__(self, body: str):
        if not isinstance(body, str):
            raise TypeError(f"Expression body must be a string, got {type(body)}")
        self._body = body

    @property
    def body(self) -> str:
        """The string representation of the expression."""

        return self._body

    def __repr__(self) -> str:
        return f"Expression('{self.body}')"

    def __str__(self) -> str:
        return self.body

    def check_syntax(self) -> Optional[SyntaxError]:
        """Force parsing of the expression.

        It is not necessary to call this method explicitly, as the expression will be
        parsed automatically when it is evaluated. However, this method can be used
        to force the parsing to happen at a specific time, for example to catch
        syntax errors early.

        Returns:
            None if the expression is valid, or a SyntaxError otherwise.
        """

        try:
            self._parse_ast()
        except SyntaxError as error:
            return error

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> Any:
        """Evaluate an expression on specific values for its variables.

        Args:
            variables: a mapping of variable names to their values.
                The variables the expression depends upon will be replaced by the values
                in this mapping.
                The mapping is also concatenated with the :data:`BUILTINS` dictionary.

        Raises:
            EvaluationError: if an error occurred during evaluation.
        """

        return self._evaluate({str(expr): variables[expr] for expr in variables})

    def _evaluate(self, variables: Mapping[str, Any]) -> Any:
        try:
            value = eval(self._code, {"__builtins__": BUILTINS}, variables)
        except Exception as error:
            raise EvaluationError(f"Could not evaluate <{self.body}>") from error
        return value

    @cached_property
    def upstream_variables(self) -> frozenset[VariableName]:
        """Return the name of the other variables the expression depend on."""

        variables = set()

        class FindNameVisitor(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                if isinstance(node.ctx, ast.Load):
                    if node.id not in BUILTINS:
                        variables.add(VariableName(node.id))

        FindNameVisitor().visit(self._ast)
        return frozenset(variables)

    @cached_property
    def _ast(self) -> ast.Expression:
        """Computes the abstract syntax tree for this expression"""

        return self._parse_ast()

    def _parse_ast(self) -> ast.Expression:
        expr = self.body

        expr = expr.replace("%", "*(1e-2)")
        expr = expr.replace("°", "*deg")
        expr = add_implicit_multiplication(expr)

        return ast.parse(expr, mode="eval")

    @cached_property
    def _code(self):
        return compile(self._ast, filename="<string>", mode="eval")

    def __eq__(self, other):
        if isinstance(other, Expression):
            return self.body == other.body
        else:
            return NotImplemented

    def __getstate__(self):
        return {"body": self.body}

    def __setstate__(self, state):
        self.__init__(**state)


serialization.register_unstructure_hook(Expression, lambda expr: expr.body)
serialization.register_structure_hook(Expression, lambda body, _: Expression(body))


def add_implicit_multiplication(source: str) -> str:
    """This adds a multiplication symbol where it would be understood as
    being implicit by the normal way algebraic equations are written but would
    be a SyntaxError in Python. Thus we have::

        2n -> 2*n
        n 2 -> n* 2
        2(a+b) -> 2*(a+b)
        (a+b)2 -> (a+b)*2
        2 3 -> 2* 3
        m n -> m* n
        (a+b)c -> (a+b)*c

    The obvious one (in algebra) being left out is something like ``n(...)``
    which is a function call - and thus valid Python syntax.
    """

    tokens = token_utils.tokenize(source)
    if not tokens:
        return tokens

    prev_token = tokens[0]
    new_tokens = [prev_token]

    for token in tokens[1:]:
        if (
            (
                prev_token.is_number()
                and (token.is_identifier() or token.is_number() or token == "(")
            )
            or (
                prev_token.is_identifier()
                and (token.is_identifier() or token.is_number())
            )
            or (prev_token == ")" and (token.is_identifier() or token.is_number()))
        ):
            new_tokens.append("*")
        new_tokens.append(token)
        prev_token = token

    return token_utils.untokenize(new_tokens)
