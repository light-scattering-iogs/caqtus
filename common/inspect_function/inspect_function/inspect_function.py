from inspect import signature


def get_parameters(f) -> list[str]:
    """Get the parameters of a function.

    Args:
        f: The function to get the parameters of.

    Returns:
        A list of the names of the parameters of the function `f`.
    """

    return list(signature(f).parameters)[1:]
