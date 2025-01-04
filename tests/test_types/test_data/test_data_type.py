from hypothesis import given
from hypothesis.strategies import data
from numpy.testing import assert_equal

from caqtus.types.data import DataType
from .data_type import data_types


@given(data(), data_types())
def test_data_values(data, dtype: DataType):
    value = data.draw(dtype.value_strategy())

    unstructured = dtype.dumps(value)
    structured = dtype.loads(unstructured)
    assert_equal(value, structured)
