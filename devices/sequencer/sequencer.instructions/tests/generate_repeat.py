from hypothesis.strategies import composite, integers

from sequencer.instructions.struct_array_instruction import Repeat
from .generate_pattern import generate_pattern


@composite
def generate_repeat(draw, max_repetitions: int, max_sub_instruction_length) -> Repeat:
    repetitions = draw(integers(min_value=2, max_value=max_repetitions))
    sub_instruction_length = draw(
        integers(min_value=1, max_value=max_sub_instruction_length)
    )

    instr = generate_pattern(sub_instruction_length)
    return repetitions * instr
