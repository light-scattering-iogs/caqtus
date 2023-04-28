from units import AnalogValue
from variable.namespace import VariableNamespace


class SequenceContext:
    def __init__(self, variables: VariableNamespace[AnalogValue]):
        self.variables: VariableNamespace[AnalogValue] = variables
        self.shot_numbers: dict[str, int] = {}
