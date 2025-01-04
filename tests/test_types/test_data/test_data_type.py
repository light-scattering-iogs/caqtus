from hypothesis import given
from .data_type import data_types
from .data_values import data_values, dtypes_and_values


@given(dtypes_and_values())
def test_data_values(args):
    dtype, value = args
    print(dtype, value)
