from typing import NewType, Any, TypeGuard

DataLabel = NewType("DataLabel", str)


def is_data_label(label: Any) -> TypeGuard[DataLabel]:
    """Check if label has a valid data label type."""
    return isinstance(label, str)
