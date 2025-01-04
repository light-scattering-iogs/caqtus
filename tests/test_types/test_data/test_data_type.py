from hypothesis import given

from .data_values import dtypes_and_values


@given(dtypes_and_values())
def test_data_values(args):
    dtype, value = args
    validator = dtype.validator()
    assert validator(value)
