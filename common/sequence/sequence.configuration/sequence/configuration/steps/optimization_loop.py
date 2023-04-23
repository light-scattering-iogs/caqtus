from typing import Optional, Self

import yaml

from expression import Expression
from sequence.configuration.steps.step import compute_total_number_shots, Step
from settings_model import SettingsModel, YAMLSerializable
from variable.name import DottedVariableName

OptimizerName = str


class VariableRange(SettingsModel):
    first_bound: Expression
    second_bound: Expression
    initial_value: Expression


class OptimizationLoop(Step, YAMLSerializable):
    def __init__(
        self,
        optimizer_name: OptimizerName,
        variables: dict[DottedVariableName, VariableRange],
        repetitions: int,
        parent: Optional[Step] = None,
        children: Optional[list[Step]] = None,
    ):
        self.optimizer_name = optimizer_name
        self.variables = variables
        self.repetitions = repetitions
        if not children:
            children = []
        super().__init__(self, parent, children)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, optimization_step: Self):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "optimizer_name": optimization_step.optimizer_name,
                "variables": optimization_step.variables,
                "repetitions": optimization_step.repetitions,
                "children": [child for child in optimization_step.children],
            },
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        mapping = loader.construct_mapping(node)
        try:
            return cls(**mapping)
        except Exception as e:
            raise ValueError(f"Cannot construct {cls.__name__} from {mapping}") from e

    def __eq__(self, other):
        if not isinstance(other, OptimizationLoop):
            return False
        return (
            self.optimizer_name == other.optimizer_name
            and self.variables == other.variables
            and self.repetitions == other.repetitions
            and self.children == other.children
        )

    def expected_number_shots(self) -> Optional[int]:
        number_sub_steps = compute_total_number_shots(self.children)
        if number_sub_steps is None:
            return None
        return self.repetitions * number_sub_steps

    @classmethod
    def empty_loop(cls):
        return cls("", {}, 0)
