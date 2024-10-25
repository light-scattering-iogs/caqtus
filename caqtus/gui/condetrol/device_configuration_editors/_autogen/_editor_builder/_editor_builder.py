from .._value_editor import ValueEditor


class EditorBuilder:
    def __init__(self) -> None:
        self._type_editors: dict[type, type[ValueEditor]] = {}

    def build_editor_for_type[T](self, type_: type[T]) -> type[ValueEditor[T]]:
        """Construct an editor for a given type.

        Raises:
            TypeNotRegisteredError, if the builder doesn't know how to construct the
            editor for the given type.
        """

        try:
            return self._type_editors[type_]
        except KeyError:
            raise TypeNotRegisteredError(
                f"Type {type_} is not registered for the editor builder"
            ) from None

    def register_editor_for_type[
        T
    ](self, type_: type[T], editor_type: type[ValueEditor[T]]) -> None:
        """Specify an editor to use when encountering a given type."""

        self._type_editors[type_] = editor_type


class TypeNotRegisteredError(ValueError):
    pass
