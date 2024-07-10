import cattrs.strategies

from caqtus.types.expression import Expression
from caqtus.utils.serialization import copy_converter
from .transformation import EvaluableOutput, Transformation

converter = copy_converter()


def structure_evaluable_output(data, _) -> EvaluableOutput:
    if isinstance(data, str):
        return Expression(data)
    else:
        return converter.structure(data, Transformation)


def get_converter() -> cattrs.Converter:
    return converter.copy()
