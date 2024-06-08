from __future__ import annotations

import attrs

from caqtus.types.expression import Expression
from ..channel_output import ChannelOutput


@attrs.define
class Constant(ChannelOutput):
    """Indicates that the output should be held at a constant value during the shot."""

    value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return str(self.value)
