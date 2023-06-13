from scipy.special import voigt_profile


def voigt(x, x0, σ, γ, A, b=0):
    return A * voigt_profile(x - x0, σ, γ) / voigt_profile(0, σ, γ) + b
