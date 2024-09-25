from __future__ import annotations

import attrs

from caqtus.utils.serialization import JSON


@attrs.frozen
class Error:
    """Represents an error that occurred during the execution of a procedure.

    Attributes:
        code: The error code.
            Values between -32768 and -32000 are reserved for pre-defined errors.
        message: The error message.
        data: Additional data that can help to understand the error.
    """

    code: int = attrs.field()
    message: str = attrs.field()
    data: JSON = attrs.field(factory=dict)
