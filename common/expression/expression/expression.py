import ast
from functools import cached_property

import token_utils
import yaml

from settings_model import YAMLSerializable
import numpy


class Expression(YAMLSerializable):
    """Python expression that can be evaluated to return a python object

    It may depend on other upstream variables that must be specified for evaluation.
    """

    def __init__(self, body: str = ""):
        self._body = body
        self._last_value = None
        self._last_evaluation_variables = None

    @property
    def body(self) -> str:
        return self._body

    @body.setter
    def body(self, value: str):
        self._body = value
        if hasattr(self, "ast"):
            del self.ast
        if hasattr(self, "code"):
            del self.code
        if hasattr(self, "upstream_variables"):
            del self.upstream_variables

    def __repr__(self):
        return f"Expression({self.body})"

    def evaluate(self, variables: dict[str]):
        """Evaluate an expression on specific values for its variables"""

        # Only keep the variables the expression actually depends of. This allow to
        # cache the last evaluation if these variables don't change but some other do.
        useful_variables = set(variables) & self.upstream_variables
        return self._evaluate({expr: variables[expr] for expr in useful_variables})

    def _evaluate(self, variables: dict[str]):
        if variables == self._last_evaluation_variables:
            return self._last_value
        else:
            variables |= dict(cos = numpy.cos, sin = numpy.sin, pi = numpy.pi)
            self._last_value = eval(self.code, variables)
            return self._last_value

    @cached_property
    def upstream_variables(self) -> frozenset[str]:
        """Return the name of the other variables the expression depend of"""

        variables = set()

        class FindNameVisitor(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                if isinstance(node.ctx, ast.Load):
                    variables.add(node.id)

        FindNameVisitor().visit(self.ast)
        return frozenset(variables)

    @cached_property
    def ast(self) -> ast.Expression:
        """Computes the abstract syntax tree for this expression"""

        explicit_expr = add_implicit_multiplication(self.body.replace("%", "*(1e-2)"))
        return ast.parse(explicit_expr, mode="eval")

    @cached_property
    def code(self):
        return compile(self.ast, filename="<string>", mode="eval")

    @classmethod
    def representer(cls, dumper: yaml.Dumper, expr: "Expression"):
        return dumper.represent_scalar(
            f"!{cls.__name__}",
            expr.body,
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(body=loader.construct_scalar(node))


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
