import functools

import cattrs
import cattrs.strategies

from caqtus.utils.serialization import copy_converter
from .transformation import Transformation


def get_converter() -> cattrs.Converter:
    converter = copy_converter()

    cattrs.strategies.include_subclasses(
        Transformation,
        converter=converter,
        union_strategy=functools.partial(
            cattrs.strategies.configure_tagged_union, tag_name="type"
        ),
    )
    return converter
