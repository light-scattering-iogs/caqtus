from returns.result import Success

from .._kernel import ExperimentKernel


async def run_sequence(kernel: ExperimentKernel, sequence_path: str) -> Success[None]:
    """Run a sequence of instructions on the setup.

    Args:
        kernel: The experiment kernel that gives access to the setup.
        sequence_path: The path to the sequence file.
    """

    return Success(None)
