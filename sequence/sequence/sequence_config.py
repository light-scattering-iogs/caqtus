from abc import ABC
from typing import Optional

import yaml
from anytree import NodeMixin
from expression import Expression

from settings_model import SettingsModel
from settings_model.settings_model import YAMLSerializable
from shot import ShotConfiguration


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

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))


class VariableDeclaration(Step, YAMLSerializable):
    def __init__(
        self, name: str, expression: Expression, parent: Optional["Step"] = None
    ):
        super().__init__(parent, None)
        self.name = name
        self.expression = expression

    def __repr__(self):
        return f"VariableDeclaration({self.name}, {self.expression})"

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "VariableDeclaration"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"name": step.name, "expression": step.expression},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))


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


class ExecuteShot(Step, YAMLSerializable):
    def __init__(self, name: str, configuration: ShotConfiguration, parent: Optional[Step] = None):
        super().__init__(parent, None)
        self.name = name
        self.configuration = configuration

    @classmethod
    def representer(cls, dumper: yaml.Dumper, step: "ExecuteShot"):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {"name": step.name, "configuration": step.configuration},
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(**loader.construct_mapping(node, deep=True))


class SequenceConfig(SettingsModel):
    program: SequenceSteps
