import numpy as np

def gaussian(x, x0, σ, A, b=0, **kwargs):
    """Compute a Gaussian function.

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

    return A * np.exp(-((x - x0) ** 2) / (2 * σ**2)) + b
