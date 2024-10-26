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
            import attrs

            from ._attrs import build_editor_for_attrs_class

            if attrs.has(type_):
                return build_editor_for_attrs_class(type_, self)
            raise TypeNotRegisteredError(
                f"Type {type_} is not registered for the editor builder"
            ) from None

    def register_editor_for_type[
        T
    ](self, type_: type[T], editor_type: type[ValueEditor[T]]) -> None:
        """Specify an editor to use when encountering a given type."""

        self._type_editors[type_] = editor_type

    def build_editor(self, type_: type) -> type[ValueEditor]:
        """Construct a gui class to edit value of a given type.

        Raises:
            EditorBuilding error if something goes wrong.
        """

        if isinstance(type_, type):
            return self.build_editor_for_type(type_)
        else:
            raise EditorBuildingError(f"Cannot build editor for {type_}")


class EditorBuildingError(Exception):
    pass


class TypeNotRegisteredError(EditorBuildingError):
    pass
