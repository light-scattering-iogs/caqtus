from variable.namespace import VariableNamespace


class SequenceContext:
    def __init__(self, variables: VariableNamespace):
        self.variables = variables
        self.shot_numbers: dict[str, int] = {}
