from ._value_editor import ValueEditor


class EditorBuilder:
    def __init__(self) -> None:
        self._type_editors: dict[type, type[ValueEditor]] = {}

    def build_editor_for_type[T](self, type_: type[T]) -> type[ValueEditor[T]]:
        return self._type_editors[type_]

    def register_editor_for_type[
        T
    ](self, type_: type[T], editor_type: type[ValueEditor[T]]) -> None:
        self._type_editors[type_] = editor_type
