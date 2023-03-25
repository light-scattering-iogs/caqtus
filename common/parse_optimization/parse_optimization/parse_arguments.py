import argparse


def get_parser() -> argparse.ArgumentParser:
    """Returns an argument parser for an optimization script."""

    parser = argparse.ArgumentParser(
        prog="cost function", description="Computes a cost function from series of shots."
    )
    parser.add_argument("current_sequence_path", type=str, help="Path to the sequence being optimized.")
    return parser
