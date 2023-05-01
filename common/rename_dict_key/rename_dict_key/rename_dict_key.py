from typing import TypeVar

_K = TypeVar("_K")
_T = TypeVar("_T")


def rename_dict_key(d: dict[_K, _T], old_key: _K, new_key: _K) -> dict[_K, _T]:
    """Return a new dictionary with the key `old_key` renamed to `new_key`.

    This function preserves the order of the dictionary.

    Parameters:
        d: The dictionary to rename the key in.
        old_key: The key to rename.
        new_key: The new name of the key.

    Returns:
        A new dictionary with the key `old_key` renamed to `new_key`. If `old_key` is not in `d`, then `d` is returned.

    Raises:
        ValueError: If `new_key` already exists in `d` and is not equal to `old_key`.
    """

    if old_key == new_key:
        return d.copy()

    if new_key in d:
        raise ValueError(f"Key {new_key} already exists in the dictionary.")

    return {_rename_key(key, old_key, new_key): value for key, value in d.items()}


def _rename_key(key: _K, old_key: _K, new_key: _K) -> _K:
    if key == old_key:
        return new_key
    else:
        return key
