import pytest
from PyQt6.QtCore import QModelIndex, Qt

from mapping_model import MappingModel


@pytest.fixture
def mapping_model():
    # Create an instance of MappingModel
    model = MappingModel()
    # Set up a sample mapping
    sample_mapping = {"key1": "value1", "key2": "value2", "key3": "value3"}
    model.set_mapping(sample_mapping)
    return model


def test_row_count(mapping_model):
    assert mapping_model.rowCount() == 3


def test_column_count(mapping_model):
    assert mapping_model.columnCount() == 2


def test_data(mapping_model):
    # Test the data in the first column
    assert mapping_model.data(mapping_model.index(0, 0)) == "key1"
    assert mapping_model.data(mapping_model.index(1, 0)) == "key2"
    assert mapping_model.data(mapping_model.index(2, 0)) == "key3"

    # Test the data in the second column
    assert mapping_model.data(mapping_model.index(0, 1)) == "value1"
    assert mapping_model.data(mapping_model.index(1, 1)) == "value2"
    assert mapping_model.data(mapping_model.index(2, 1)) == "value3"

    # Test invalid index
    assert mapping_model.data(QModelIndex()) is None


def test_flags(mapping_model):
    # Test the flags for valid indices
    assert (
        mapping_model.flags(mapping_model.index(0, 0))
        == Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    )
    assert (
        mapping_model.flags(mapping_model.index(0, 1))
        == Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    )

    # Test the flags for invalid index
    assert mapping_model.flags(QModelIndex()) == Qt.ItemFlag.NoItemFlags
