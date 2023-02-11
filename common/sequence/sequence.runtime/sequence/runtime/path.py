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

    def __eq__(self, other):
        if isinstance(other, SequencePath):
            return self._path == other._path
        elif isinstance(other, str):
            return self._path == other
        return False

    def get_ancestors(self, strict: bool = True) -> list["SequencePath"]:
        ancestors = self._path.split(_PATH_SEPARATOR)
        if strict:
            *ancestors, _ = ancestors

        result = []
        ancestor = ""
        for name in ancestors:
            ancestor = f"{ancestor}{_PATH_SEPARATOR}{name}" if ancestor else name
            result.append(SequencePath(ancestor))
        return result
