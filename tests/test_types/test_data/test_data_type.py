from hypothesis import given, example
from numpy.testing import assert_equal

from caqtus.types.data import Struct, Int
from .data_values import dtypes_and_values


@given(dtypes_and_values())
def test_data_values(args):
    dtype, value = args

    unstructured = dtype.dumps(value)
    structured = dtype.loads(unstructured)
    assert_equal(value, structured)
