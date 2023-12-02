from sequencer.instructions.struct_array_instruction import Pattern


def test():
    a = Pattern([1, 2, 3])
    assert a[0] == 1
    assert a[0:2] == Pattern([1, 2])
