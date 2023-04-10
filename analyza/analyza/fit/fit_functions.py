import numpy as np
from scipy.special import voigt_profile


def linear_function(x, a, b=0, **kwargs):
    """Compute an affine function.

    This function is defined as:
    .. math::
        f(x) = a x + b

    Args:
        x: The independent variable.
        a: The slope of the function.
        b: The intercept of the function.
    """

    return a * x + b


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


def lorentzian(x, x0, γ, A, b=0, **kwargs):
    """Compute a Lorentzian function.

    This function is defined as:
    .. math::
        f(x) = \\frac{A}{1 + \\left(\\frac{x - x_0}{\\gamma}\\right)^2} + b

    Args:
        x: The independent variable.
        x0: The position of the peak.
        γ: The half-width at half value of the peak.
    """

    return A / (1 + (x - x0) ** 2 / γ**2) + b

def gaussian(x, x0, σ, A, b=0, **kwargs):
    """ Compute a Gaussian function.

    This function is defined as:
    .. math::
        f(x) = A \exp(-\frac{(x - x_0)^2}{2 \sigma^2}) + b

    Args:
        x: The independent variable.
        x0: The position of the peak.
        σ: The standard deviation of the peak.
        A: The amplitude of the peak.
        b: The background offset.
    """

    return A*np.exp(-(x-x0)**2/(2*σ**2)) + b


def voigt(x, x0, σ, γ, A, b=0):
    return A * voigt_profile(x - x0, σ, γ) / voigt_profile(0, σ, γ) + b
