import ast
from collections.abc import Mapping
from copy import deepcopy
from functools import cached_property
from typing import Optional, Any

import numpy
import token_utils
import yaml
from scipy.signal import sawtooth

from settings_model import YAMLSerializable
from util import serialization
from variable.name import VariableName, DottedVariableName


def square_wave(t, period, duty_cycle=0.5, low=0, high=1):
    x = t / period
    x = x - numpy.floor(x)
    is_high = x < duty_cycle
    result = numpy.where(is_high, high, low)
    return result


BUILTINS = {
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
    "sawtooth": sawtooth,
    "square_wave": square_wave,
    "max": max,
    "min": min,
}


class Expression:
    """Python expression that can be evaluated to return a python object

    It may depend on other upstream variables that must be specified during evaluation.
    """

    def __init__(
        self,
        body: str,
        builtins: Optional[dict[str, Any]] = None,
        implicit_multiplication: bool = True,
        allow_percentage: bool = True,
        cache_evaluation: bool = True,
    ):
        """
        Args:
            body: the expression body. This is a string expression that must follow the
            specifications of the python syntax.
            builtins: a dictionary of builtin functions and constants that can be used
            in the expression. they will be available in the expression namespace, but
            are not included in the upstream variables.
            implicit_multiplication: if True, the expression will be parsed to allow
            implicit multiplication, even though it is not regular python. for example,
            'a b' will be parsed as 'a * b'. if set to False, a syntax error will be
            raised in such cases.
            allow_percentage: if True, the expression will be parsed to understand the
            use of the % symbol as a multiplication by 0.01. if set to False, the %
            symbol will be understood as a modulo operator.
        """
        if builtins is None:
            builtins = BUILTINS
        self.body = body
        self._last_value = None
        self._last_evaluation_variables = None
        self._builtins = builtins
        self._implicit_multiplication = implicit_multiplication
        self._allow_percentage = allow_percentage
        self._cache_evaluation = cache_evaluation

    @property
    def body(self) -> str:
        return self._body

    # noinspection PyPropertyAccess
    @body.setter
    def body(self, value):
        if not isinstance(value, str):
            raise TypeError("Expression body must be a string")
        self._body = value
        if hasattr(self, "ast"):
            del self.ast
        if hasattr(self, "code"):
            del self.code
        if hasattr(self, "upstream_variables"):
            del self.upstream_variables

    def __repr__(self) -> str:
        return f"Expression({self.body})"

    def __str__(self) -> str:
        return self.body

    def evaluate(self, variables: Mapping[DottedVariableName, Any]) -> Any:
        """Evaluate an expression on specific values for its variables"""
        # Only keep the variables the expression actually depends on. This allows to
        # cache the last evaluation if these variables don't change but some other do.
        useful_variables = set(variables) & self.upstream_variables
        return self._evaluate({str(expr): variables[expr] for expr in useful_variables})

    def _evaluate(self, variables: Mapping[str, Any]) -> Any:
        can_use_cached_value = self._cache_evaluation and (
            variables == self._last_evaluation_variables
        )
        if can_use_cached_value:
            return self._last_value
        else:
            try:
                self._last_value = eval(
                    self.code, {"__builtins__": self._builtins}, variables
                )
            except Exception as error:
                raise EvaluationError(self.body, variables) from error
            return self._last_value

    @cached_property
    def upstream_variables(self) -> frozenset[VariableName]:
        """Return the name of the other variables the expression depend on"""

        variables = set()

        builtins = self._builtins

        class FindNameVisitor(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                if isinstance(node.ctx, ast.Load):
                    if node.id not in builtins:
                        variables.add(VariableName(node.id))

        FindNameVisitor().visit(self.ast)
        return frozenset(variables)

    @cached_property
    def ast(self) -> ast.Expression:
        """Computes the abstract syntax tree for this expression"""

        expr = self.body
        if self._allow_percentage:
            expr = expr.replace("%", "*(1e-2)")

        if self._implicit_multiplication:
            expr = add_implicit_multiplication(expr)
        try:
            return ast.parse(expr, mode="eval")
        except SyntaxError as error:
            raise SyntaxError(f"Syntax error in the expression '{expr}'") from error

    @cached_property
    def code(self):
        return compile(self.ast, filename="<string>", mode="eval")

    def __eq__(self, other):
        if isinstance(other, Expression):
            return self.body == other.body
        else:
            return False

    # This is a hack to use expressions as pydantic fields. The two methods below
    # can be removed once we remove pydantic dependency from the project.
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, Expression):
            return v
        elif isinstance(v, str):
            return Expression(v)
        else:
            raise TypeError("Expression must be a string or Expression object")


serialization.register_unstructure_hook(Expression, lambda expr: expr.body)
serialization.register_structure_hook(Expression, lambda body, _: Expression(body))


def add_implicit_multiplication(source: str) -> str:
    """This adds a multiplication symbol where it would be understood as
    being implicit by the normal way algebraic equations are written but would
    be a SyntaxError in Python. Thus we have::

        2n  -> 2*n
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


class EvaluationError(Exception):
    def __init__(self, body: str, variables: Mapping[str, Any]):
        self._body = body
        self._variables = deepcopy(variables)
        message = f"Error while evaluating expression '{body}'"
        super().__init__(message)


# YAMLSerializable will be removed in the future, the lines below are here for
# legacy until we remove it.
def expression_representer(dumper: yaml.Dumper, expr: Expression):
    cls = type(expr)
    return dumper.represent_scalar(
        f"!{cls.__name__}",
        expr.body,
    )


def expression_constructor(loader: yaml.Loader, node: yaml.Node):
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            None,
            None,
            f"Expected a scalar node but got {type(node)}",
            node.start_mark,
        )
    value = loader.construct_scalar(node)
    if not isinstance(value, str):
        raise yaml.constructor.ConstructorError(
            None,
            None,
            "Expected a string",
            node.start_mark,
        )
    return Expression(body=value)


YAMLSerializable.get_dumper().add_representer(Expression, expression_representer)
YAMLSerializable.get_loader().add_constructor(f"!Expression", expression_constructor)
