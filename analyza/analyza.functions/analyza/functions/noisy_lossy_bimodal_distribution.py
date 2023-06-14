import numpy as np
from numpy.typing import ArrayLike
from scipy.special import gammainc
from scipy.stats import norm, poisson, rv_continuous


class NoisyLossyBimodalDistribution:
    def __init__(self, max_photon_number: int):
        self._n = np.arange(0, max_photon_number)
        self._noisy_poisson = NoisyPoisson(max_photon_number)
        self._noisy_poisson_loss = NoisyPoissonLoss(max_photon_number)

    def pdf(self, x: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return (p0 * self.zero_atom_pdf(x, n0, p0, n1, p1, σ)
                + (1 - p0 - p1) * self.loss_pdf(x, n0, p0, n1, p1, σ)
                + p1 * self.one_atom_pdf(x, n0, p0, n1, p1, σ))

    def zero_atom_pdf(self, x: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return self._noisy_poisson._pdf(x, n0, σ)

    def one_atom_pdf(self, x: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return self._noisy_poisson._pdf(x, n0 + n1, σ)

    def loss_pdf(self, x: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return self._noisy_poisson_loss._pdf(x, n0, n1, σ)

    def fidelity(self, threshold: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return (self.proba_no_detection_zero_atom(threshold, n0, p0, n1, p1, σ)
                + self.proba_detection_one_atom(threshold, n0, p0, n1, p1, σ)
                + self.proba_detection_loss(threshold, n0, p0, n1, p1, σ))

    def proba_no_detection_zero_atom(self, threshold: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return p0 * self._noisy_poisson.cdf(threshold, n0, σ)

    def proba_detection_one_atom(self, threshold: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return p1 * (1 - self._noisy_poisson.cdf(threshold, n0 + n1, σ))

    def proba_detection_loss(self, threshold: ArrayLike, n0: int, p0: float, n1: int, p1: int, σ: float):
        return (1 - p0 - p1) * (1 - self._noisy_poisson_loss.cdf(threshold, n0, n1, σ))

    def _convolve_with_gaussian(self, x: ArrayLike, P, σ: float):
        return sum(p_n * norm.pdf(x, loc=n, scale=σ) for p_n, n in zip(P, self._n))


class NoisyPoisson(rv_continuous):
    def __init__(self, n_max: int):
        self._n = np.arange(0, n_max)
        super().__init__()

    def _argcheck(self, λ: float, σ: float):
        return λ >= 0 and σ > 0

    def _pdf(self, x, λ, σ):
        P = poisson.pmf(self._n, λ)
        return sum(p_n * norm.pdf(x, loc=n, scale=σ) for p_n, n in zip(P, self._n))

    def _cdf(self, x, λ, σ):
        P = poisson.pmf(self._n, λ)
        return sum(p_n * norm.cdf(x, loc=n, scale=σ) for p_n, n in zip(P, self._n))


class NoisyPoissonLoss(rv_continuous):
    def __init__(self, n_max: int):
        self._n = np.arange(0, n_max)
        super().__init__()

    def _argcheck(self, λ0: float, λ1: float, σ: float):
        return (0 <= λ0 < λ1) and σ > 0

    def _pdf(self, x: ArrayLike, λ0: float, λ1: float, σ: float):
        P = (gammainc(self._n + 1, λ0 + λ1) - gammainc(self._n + 1, λ0)) / λ1
        return sum(p_n * norm.pdf(x, loc=n, scale=σ) for p_n, n in zip(P, self._n))

    def _cdf(self, x: ArrayLike, λ0: float, λ1: float, σ: float):
        P = (gammainc(self._n + 1, λ0 + λ1) - gammainc(self._n + 1, λ0)) / λ1
        return sum(p_n * norm.cdf(x, loc=n, scale=σ) for p_n, n in zip(P, self._n))
