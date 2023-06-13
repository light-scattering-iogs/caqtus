import numpy as np


def exponential_decay(t, τ, A, b=0, **kwargs):
    """Compute a function that decays exponentially.

    This function is defined as:
    .. math::
        f(t) = A \exp(-t/ \tau ) + b

    Args:
        t: The independent variable.
        τ: The decay time constant.
        A: The amplitude of the function.
        b: The background offset.
    """

    return A * np.exp(-t / τ) + b


# noinspection NonAsciiCharacters
def exponential_saturation(t, τ, A, b=0, **kwargs):
    """Compute a function that saturates exponentially.

    This function is defined as:

    .. math::
        f(t) = A \exp(-t/ \tau ) - 1 ) + b

    Args:
        t: The independent variable.
        τ: The decay time constant.
        A: The final value the function saturates to.
        b: The background offset.
    """

    return A * (1 - np.exp(-t / τ)) + b
