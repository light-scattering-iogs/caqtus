import abc
from collections.abc import MutableSequence
from typing import TypeVar

import attrs

from core.types.expression import Expression

T = TypeVar("T")


@attrs.define
class TimeLane(MutableSequence[T], abc.ABC):
    values: list[T] = attrs.field(factory=list)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, item) -> T:
        if isinstance(item, int):
            return self.get_index(item)
        else:
            raise TypeError(f"Invalid type for index: {type(item)}")

    def get_index(self, index: int) -> T:
        return self.values[index]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.set_index(key, value)
        else:
            raise TypeError(f"Invalid type for index: {type(key)}")

    def set_index(self, index: int, value: T):
        self.values[index] = value

    def __delitem__(self, key):
        if isinstance(key, int):
            self.delete_index(key)
        else:
            raise TypeError(f"Invalid type for index: {type(key)}")

    def delete_index(self, index: int):
        del self.values[index]

    def insert(self, index: int, value: T):
        self.values.insert(index, value)


@attrs.define
class TimeLanes:
    step_names: list[str] = attrs.field(
        factory=list,
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=attrs.validators.instance_of(str),
        ),
        on_setattr=attrs.setters.validate,
    )
    step_durations: list[Expression] = attrs.field(
        factory=list,
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=attrs.validators.instance_of(Expression),
        ),
        on_setattr=attrs.setters.validate,
    )
    lanes: dict[str, TimeLane] = attrs.field(
        factory=dict,
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.instance_of(str),
            value_validator=attrs.validators.instance_of(TimeLane),
        ),
        on_setattr=attrs.setters.validate,
    )

    @property
    def number_steps(self) -> int:
        return len(self.step_names)

    @property
    def number_lanes(self) -> int:
        return len(self.lanes)
