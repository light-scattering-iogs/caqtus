import argparse
from pathlib import Path

from pre_scripted_move import MoveConfiguration
from trap_signal_generator.configuration import StaticTrapConfiguration2D

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a configuration to move a pattern of tweezers."
    )
    parser.add_argument(
        "-i", "--initial_traps", help="Path to initial trap configuration.", type=Path
    )
    parser.add_argument(
        "-f", "--final_traps", help="Path to final trap configuration.", type=Path
    )
    parser.add_argument(
        "-s", "--number_samples", help="Number of samples for the move.", type=int
    )
    parser.add_argument("-o", "--output", help="Output file name.", type=Path)

    args = parser.parse_args()

    initial_traps = args.initial_traps
    with open(initial_traps, "r") as f:
        initial_config = StaticTrapConfiguration2D.from_yaml(f.read())

    final_traps = args.final_traps
    with open(final_traps, "r") as f:
        final_config = StaticTrapConfiguration2D.from_yaml(f.read())

    move_config = MoveConfiguration(
        initial_config=initial_config,
        final_config=final_config,
        move_number_samples=args.number_samples,
    )

    with open(args.output, "w") as f:
        f.write(move_config.to_yaml())
