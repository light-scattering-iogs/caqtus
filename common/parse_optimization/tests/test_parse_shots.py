from parse_optimization import parse_shots, write_shots

from sequence.runtime import Sequence, Shot


def test_parse_shots():
    # Test case 1: A simple string with one shot
    string1 = "Sequence1:Shot1:0"
    sequence1 = Sequence("Sequence1")
    expected_result1 = [Shot(sequence1, "Shot1", 0)]
    assert parse_shots(string1) == expected_result1

    # Test case 2: A string with multiple shots
    string2 = "Sequence1:Shot1:0, Sequence2:Shot2:1, Sequence3:Shot3:2"
    sequence1 = Sequence("Sequence1")
    sequence2 = Sequence("Sequence2")
    sequence3 = Sequence("Sequence3")
    expected_result2 = [
        Shot(sequence1, "Shot1", 0),
        Shot(sequence2, "Shot2", 1),
        Shot(sequence3, "Shot3", 2),
    ]
    assert parse_shots(string2) == expected_result2

    # Test case 3: A string with no shots
    string3 = ""
    expected_result3 = []
    assert parse_shots(string3) == expected_result3


def test_round_trip():
    sequence1 = Sequence("Sequence1")
    shots = [Shot(sequence1, "shot", 0), Shot(sequence1, "shot", 1)]
    string = write_shots(shots)
    assert parse_shots(string) == shots
