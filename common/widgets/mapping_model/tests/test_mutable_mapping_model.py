from PyQt6.QtCore import Qt
from mapping_model import MutableMappingModel


def test_setMapping():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.data(model.index(0, 0)) == "key1"
    assert model.data(model.index(0, 1)) == "value1"
    assert model.data(model.index(1, 0)) == "key2"
    assert model.data(model.index(1, 1)) == "value2"


def test_getMapping():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert model.get_mapping() == mapping


def test_data():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "key1"
    assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "value1"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.EditRole) == "key1"
    assert model.data(model.index(0, 1), Qt.ItemDataRole.EditRole) == "value1"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) is None
    assert model.data(model.index(0, 1), Qt.ItemDataRole.UserRole) is None


def test_setData():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert model.setData(model.index(0, 0), "new_key", Qt.ItemDataRole.EditRole)
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "new_key"

    assert model.setData(model.index(0, 1), "new_value", Qt.ItemDataRole.EditRole)
    assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "new_value"

    assert not model.setData(
        model.index(0, 0), "invalid_key", Qt.ItemDataRole.DisplayRole
    )


def test_flags():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert (
        model.flags(model.index(0, 0))
        == Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
        | Qt.ItemFlag.ItemIsEditable
    )
    assert (
        model.flags(model.index(0, 1))
        == Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
        | Qt.ItemFlag.ItemIsEditable
    )


def test_insertRow():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert model.insert_row(1, "new_key", "new_value")

    assert model.rowCount() == 3
    assert model.columnCount() == 2
    assert model.data(model.index(0, 0)) == "key1"
    assert model.data(model.index(0, 1)) == "value1"
    assert model.data(model.index(1, 0)) == "new_key"
    assert model.data(model.index(1, 1)) == "new_value"
    assert model.data(model.index(2, 0)) == "key2"
    assert model.data(model.index(2, 1)) == "value2"

    assert not model.insert_row(5, "key3", "value3")


def test_removeRows():
    model = MutableMappingModel()
    mapping = {"key1": "value1", "key2": "value2"}
    model.set_mapping(mapping)

    assert model.removeRows(0, 1)

    assert model.rowCount() == 1
    assert model.columnCount() == 2
    assert model.data(model.index(0, 0)) == "key2"
    assert model.data(model.index(0, 1)) == "value2"

    assert not model.removeRows(1, 1)
