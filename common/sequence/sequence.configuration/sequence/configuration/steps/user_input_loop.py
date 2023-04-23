from typing import Optional, Self

import yaml

from sequence.configuration.steps.step import Step
from settings_model import YAMLSerializable, validate_arguments
from variable.name import DottedVariableName
from .optimization_loop import VariableRange


class UserInputLoop(Step, YAMLSerializable):
    """Holds the information for a loop asking the user to input variable values."""

    iteration_variables: dict[DottedVariableName, VariableRange]

    def __init__(
        self,
        iteration_variables: dict[DottedVariableName, VariableRange],
        parent: Optional[Step] = None,
        children: Optional[list[Step]] = None,
    ):
        self.iteration_variables = iteration_variables
        if not children:
            children = []
        Step.__init__(self, parent, children)

    @property
    def iteration_variables(self) -> dict[DottedVariableName, VariableRange]:
        return self._iteration_variables

    @iteration_variables.setter
    @validate_arguments
    def iteration_variables(
        self, iteration_variables: dict[DottedVariableName, VariableRange]
    ):
        self._iteration_variables = iteration_variables

    @classmethod
    def representer(cls, dumper: yaml.Dumper, user_input_loop: Self):
        return dumper.represent_mapping(
            f"!{cls.__name__}",
            {
                "iteration_variables": user_input_loop.iteration_variables,
                "children": [child for child in user_input_loop.children],
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
        if not isinstance(other, UserInputLoop):
            return False
        return (
            self.iteration_variables == other.iteration_variables
            and self.children == other.children
        )

    def expected_number_shots(self) -> Optional[int]:
        # We don't when the user will stop the loop,
        # so we return None
        return None

    @classmethod
    def empty_loop(cls) -> Self:
        return cls({})
