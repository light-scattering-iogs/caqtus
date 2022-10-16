import ast
from functools import cached_property

import yaml

from settings_model import YAMLSerializable


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

        return ast.parse(self.body, mode="eval")

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
