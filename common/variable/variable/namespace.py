from typing import dataclass_transform


_FIELDS = "__namespace_fields__"


class VariableField:
    def __init__(self, default=None):
        self._default = default

    def __set_name__(self, owner, name):
        if not issubclass(owner, Namespace):
            raise TypeError
        self._name = name
        self._private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if hasattr(obj, self._private_name):
            return getattr(obj, self._private_name)
        else:
            raise AttributeError

    def __set__(self, obj, value):
        setattr(obj, self._private_name, value)
        for callback in obj._change_callbacks[self._name]:
            callback(value)


@dataclass_transform()
class Namespace:
    def __init__(self, **kwargs):
        pass

    def __init_subclass__(cls, **kwargs):
        fields = {}

        has_dataclass_bases = False
        for b in cls.__mro__[-1:0:-1]:
            base_fields = getattr(b, _FIELDS, None)
            if base_fields is not None:
                has_dataclass_bases = True
                for f in base_fields.values():
                    fields[f.name] = f

        cls_annotations = cls.__dict__.get("__annotations__", {})
        cls_fields = []
        for name, type in cls_annotations.items():
            cls_fields.append(_get_field(cls, name, type))

        for f in cls_fields:
            fields[f.name] = f


class VariableNamespace(Namespace):
    a: int = VariableField()


v = VariableNamespace(a=12, b=12)
