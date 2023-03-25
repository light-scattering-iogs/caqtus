import typing

from sequence.runtime import Sequence, Shot


def parse_shots(string: str) -> list[Shot]:
    """Parse a string of shots into a list of Shot objects.

    Args:
        string: String of shots to parse. The string should be formatted like this:
        "sequence_path:shot_name:shot_index, sequence_path:shot_name:shot_index, ..."

    Returns:
        List of Shot objects parsed from the string. This function doesn't check that the sequences or shots
        actually exist.
    """

    if not string:
        return []

    sequences = {}

    shots = []
    for shot_string in string.split(","):
        sequence_name, shot_name, shot_index = shot_string.strip().split(":")
        if sequence_name not in sequences:
            sequence = Sequence(sequence_name)
            sequences[sequence_name] = sequence
        else:
            sequence = sequences[sequence_name]
        shots.append(Shot(sequence, shot_name, int(shot_index)))

    return sorted(shots, key=_shots_order)


def write_shots(shots: typing.Iterable[Shot]) -> str:
    """Write a list of Shot objects to a string.

    Args:
        shots: List of Shot objects to write.

    Returns:
        String of shots. The string is formatted like this:
        "sequence_path:shot_name:shot_index, sequence_path:shot_name:shot_index, ..."
    """

    return ", ".join(
        f"{shot.sequence.path}:{shot.name}:{shot.index}"
        for shot in sorted(shots, key=_shots_order)
    )


def _shots_order(shot: Shot) -> tuple[str, str, int]:
    """Return a tuple that can be used to sort shots.

    Args:
        shot: Shot to sort.

    Returns:
        Tuple that can be used to sort shots.
    """

    return str(shot.sequence.path), shot.name, shot.index
