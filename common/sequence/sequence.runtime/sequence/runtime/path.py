import re

_PATH_SEPARATOR = "/"
_PATH_NAMES_REGEX = "[a-zA-Z0-9_]+"
_PATH_REGEX = re.compile(
    f"^{_PATH_NAMES_REGEX}({_PATH_SEPARATOR}{_PATH_NAMES_REGEX})*$"
)


class SequencePath:
    # Warning: keep this object always immutable

    def __init__(self, path: str):
        if self.is_valid_path(path):
            self._path = path
        else:
            raise ValueError(f"Invalid path format: {path}")

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        return _PATH_REGEX.match(path) is not None

    def __repr__(self):
        return f"SequencePath({self._path!r})"

    def __str__(self):
        return self._path
