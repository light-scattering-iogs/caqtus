from caqtus.shot_compilation.timed_instructions import Pattern, merge_instructions


def test_shifted_loops():
    pulse = Pattern([True]) * 50 + Pattern([False]) * 50
    extra = Pattern([False]) * 30

    instr_1 = 10_000 * pulse + extra
    instr_2 = extra + 10_000 * pulse

    merged = merge_instructions(instr_1=instr_1, instr_2=instr_2)
    assert merged["instr_1"] == instr_1
    assert merged["instr_2"] == instr_2
