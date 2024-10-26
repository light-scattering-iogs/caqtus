import typing

from .._value_editor import ValueEditor

type TypeExpr[T] = typing.Any


class EditorBuilder:
    def __init__(self) -> None:
        self._type_editors: dict[TypeExpr, type[ValueEditor]] = {}

    def register_editor[
        T
    ](self, type_: TypeExpr[T], editor_type: type[ValueEditor[T]]) -> None:
        """Specify an editor to use when encountering a given type."""

        self._type_editors[type_] = editor_type

    def build_editor(self, type_: TypeExpr) -> type[ValueEditor]:
        """Construct a gui class to edit value of a given type.

        Raises:
            EditorBuilding error if something goes wrong.
        """

        try:
            return self._type_editors[type_]
        except KeyError:
            import attrs

            from ._attrs import build_editor_for_attrs_class

            if attrs.has(type_):
                return build_editor_for_attrs_class(type_, self)
            raise TypeNotRegisteredError(
                f"No editor is registered to handle {type_}"
            ) from None


class EditorBuildingError(Exception):
    pass


class TypeNotRegisteredError(EditorBuildingError):
    pass
