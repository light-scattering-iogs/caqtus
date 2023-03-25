import argparse


def get_parser() -> argparse.ArgumentParser:
    """Returns an argument parser for an optimization script."""

    parser = argparse.ArgumentParser(
        prog="cost function", description="Computes a cost function from series of shots."
    )
    return parser
