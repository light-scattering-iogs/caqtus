from abc import ABC, abstractmethod
from functools import singledispatch
from typing import Optional, Iterable

import numpy
import yaml
from anytree import NodeMixin, RenderTree

from expression import Expression
from settings_model import YAMLSerializable
from units import Quantity, units


class Step(NodeMixin, ABC):
    def __init__(
        self, parent: Optional["Step"] = None, children: Optional[list["Step"]] = None
    ):
        self.parent = parent
        if children is not None:
            self.children = children

    def row(self):
        if self.is_root:
            return 0
        else:
            for i, child in enumerate(self.parent.children):
                if child is self:
                    return i

    @abstractmethod
    def expected_number_shots(self) -> Optional[int]:
        """Return the number of shots planned inside this step

        Returns None if this is unknown.
        """
        raise NotImplementedError()


class SequenceSteps(Step, YAMLSerializable):
    def __init__(
        self, parent: Optional["Step"] = None, children: Optional[list["Step"]] = None
    ):
        if not children:
            children = []
        super().__init__(parent, children)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "SequenceSteps"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"children": [child for child in step.children]},
        )

    def __repr__(self):
        return f"SequenceSteps(parent={self.parent}, children={self.children})"

    def __str__(self):
        return "\n".join(
            f"{pre}{node if not node is self else 'steps'}"
            for pre, _, node in RenderTree(self)
        )

    def __eq__(self, other):
        if not isinstance(other, SequenceSteps):
            return False
        return self.children == other.children

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def expected_number_shots(self) -> Optional[int]:
        return _compute_total_number_shots(self.children)


class VariableDeclaration(Step, YAMLSerializable):
    def __init__(
        self, name: str, expression: Expression, parent: Optional["Step"] = None
    ):
        super().__init__(parent, None)
        self.name = name
        self.expression = expression

    def __repr__(self):
        return f"VariableDeclaration({self.name}, {self.expression})"

    def __str__(self):
        return f"{self.name} = {self.expression.body}"

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "VariableDeclaration"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"name": step.name, "expression": step.expression},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __eq__(self, other):
        if not isinstance(other, VariableDeclaration):
            return False
        return self.name == other.name and self.expression == other.expression

    def expected_number_shots(self) -> Optional[int]:
        return 0


class LinspaceLoop(Step, YAMLSerializable):
    def __init__(
        self,
        name: str,
        start: Expression,
        stop: Expression,
        num: int,
        parent: Optional["Step"] = None,
        children: Optional[list["Step"]] = None,
    ):
        if not children:
            children = []
        super().__init__(parent, children)
        self.name = name
        self.start = start
        self.stop = stop
        self.num = num

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "LinspaceLoop"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
                "start": step.start,
                "stop": step.stop,
                "num": step.num,
                "children": [child for child in step.children],
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.num} steps"
        )

    def __eq__(self, other):
        if not isinstance(other, LinspaceLoop):
            return False
        return (
            self.name == other.name
            and self.start == other.start
            and self.stop == other.stop
            and self.num == other.num
            and self.children == other.children
        )

    def expected_number_shots(self) -> Optional[int]:
        number_sub_steps = _compute_total_number_shots(self.children)
        if number_sub_steps is None:
            return None
        return self.num * number_sub_steps


class ArangeLoop(Step, YAMLSerializable):
    def __init__(
        self,
        name: str,
        start: Expression,
        stop: Expression,
        step: Expression,
        parent: Optional["Step"] = None,
        children: Optional[list["Step"]] = None,
    ):
        if not children:
            children = []
        super().__init__(parent, children)
        self.name = name
        self.start = start
        self.stop = stop
        self.step = step

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "ArangeLoop"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "name": step.name,
                "start": step.start,
                "stop": step.stop,
                "step": step.step,
                "children": [child for child in step.children],
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __str__(self):
        return (
            f"For {self.name} = {self.start.body} to {self.stop.body} with"
            f" {self.step.body} spacing"
        )

    def __eq__(self, other):
        if not isinstance(other, ArangeLoop):
            return False
        return (
            self.name == other.name
            and self.start == other.start
            and self.stop == other.stop
            and self.step == other.step
            and self.children == other.children
        )

    def expected_number_shots(self) -> Optional[int]:
        number_sub_steps = _compute_total_number_shots(self.children)
        if number_sub_steps is None:
            return None
        try:
            start = Quantity(self.start.evaluate(units))
            stop = Quantity(self.stop.evaluate(units))
            step = Quantity(self.step.evaluate(units))

            unit = start.units

            multiplier = len(
                numpy.arange(
                    start.to(unit).magnitude,
                    stop.to(unit).magnitude,
                    step.to(unit).magnitude,
                )
            )
            return multiplier * number_sub_steps
        except Exception:
            return None


class ExecuteShot(Step, YAMLSerializable):
    def __init__(self, name: str, parent: Optional[Step] = None):
        super().__init__(parent, None)
        self.name = name

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "ExecuteShot"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"name": step.name},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))

    def __str__(self):
        return f"Do {self.name}"

    def __eq__(self, other):
        if not isinstance(other, ExecuteShot):
            return False
        return self.name == other.name

    def expected_number_shots(self) -> Optional[int]:
        return 1


@singledispatch
def get_all_variable_names(_: Step) -> set[str]:
    raise NotImplementedError()


@get_all_variable_names.register
def _(steps: SequenceSteps):
    result = set()
    for step in steps.children:
        result |= get_all_variable_names(step)
    return result


@get_all_variable_names.register
def _(variable_declaration: VariableDeclaration):
    return {variable_declaration.name}


@get_all_variable_names.register
def _(linspace_loop: LinspaceLoop):
    return {linspace_loop.name}


@get_all_variable_names.register
def _(arange_loop: ArangeLoop):
    return {arange_loop.name}


@get_all_variable_names.register
def _(_: ExecuteShot):
    return set()


def _compute_total_number_shots(steps: Iterable[Step]) -> Optional[int]:
    result = 0
    for step in steps:
        step_result = step.expected_number_shots()
        if step_result is None:
            return None
        result += step_result
    return result
