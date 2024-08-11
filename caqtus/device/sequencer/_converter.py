import decimal

import cattrs.strategies

from caqtus.utils import serialization
from .trigger import TriggerEdge, Trigger

converter = serialization.copy_converter()
"""A converter than can serialize and deserialize sequencer configurations."""


def _structure_decimal(value, _) -> decimal.Decimal:
    return decimal.Decimal(value)


converter.register_structure_hook(decimal.Decimal, _structure_decimal)


def _unstructure_decimal(value) -> str:
    return str(value)


converter.register_unstructure_hook(decimal.Decimal, _unstructure_decimal)


converter.register_unstructure_hook(TriggerEdge, lambda edge: edge.value)
cattrs.strategies.configure_tagged_union(Trigger, converter, tag_name="trigger type")
