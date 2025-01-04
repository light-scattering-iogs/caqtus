from hypothesis import given, example

from caqtus.types.data import Struct, Int
from .data_values import dtypes_and_values


@given(dtypes_and_values())
@example(args=(Struct(fields={"": Int()}), {"": 0}))
def test_data_values(args):
    dtype, value = args
    unstructure_hook = dtype.get_unstructure_hook()
    unstructured = unstructure_hook(value)
