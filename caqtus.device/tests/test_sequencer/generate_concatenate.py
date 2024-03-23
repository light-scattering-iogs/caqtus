from hypothesis.strategies import composite, integers
from caqtus.device.sequencer.instructions import Concatenate

from .generate_pattern import generate_pattern


@composite
def generate_concatenate(draw, length: int, offset: int = 0) -> Concatenate:
    if length <= 1:
        raise ValueError("Length must be strictly greater than 1.")
    else:
        left_length = draw(integers(min_value=1, max_value=length - 1))
        right_length = length - left_length

        left = generate_pattern(left_length, offset=offset)
        if right_length == 1:
            right = generate_pattern(right_length, offset=offset + left_length)
        else:
            right = draw(
                generate_concatenate(right_length, offset=offset + left_length)
            )
        return left + right
