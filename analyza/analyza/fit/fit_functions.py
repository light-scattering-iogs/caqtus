import numpy as np
from scipy.special import voigt_profile


def exponential_decay(t, lifetime, amplitude, background_offset=0, *args, **kwargs):
    return amplitude * np.exp(-t / lifetime) + background_offset


# noinspection NonAsciiCharacters
def exponential_saturation(t, A, τ, b=0, *args, **kwargs):
    """Compute the following function

    .. math::
    f(t) = A \exp(-t/ \tau ) - 1 ) + b
    """
    return A * (1 - np.exp(-t / τ)) + b


def lorentzian(x, x0, γ, A, b=0, **kwargs):
    return A / (1 + (x - x0) ** 2 / γ**2) + b


def voigt(x, x0, σ, γ, A, b=0):
    return A * voigt_profile(x - x0, σ, γ) / voigt_profile(0, σ, γ) + b
