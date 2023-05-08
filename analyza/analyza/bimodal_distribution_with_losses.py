import numpy as np
from scipy.optimize import LinearConstraint
from scipy.special import erf
from scipy.stats import rv_continuous, norm


# noinspection NonAsciiCharacters
class LossyBimodalDistribution(rv_continuous):
    r"""Bimodal distribution with losses.

    This distribution is made of two gaussian lobes separated by a bridge. It is defined as:
    .. math::
    f(x) = p_0 \mathcal{N}_{\mu_0, \sigma_0}(x)
         + p_1 \mathcal{N}_{\mu_1, \sigma_1}(x)
         + (1 - p_0 - p_1) \mathcal{N}_{0, s} \ast \mathcal{U}_{\mu_0, \mu_1}(x)
    where :math:`\mathcal{N}_{\mu, \sigma}` is the normal distribution with mean :math:`\mu` and standard deviation
    :math:`\sigma` and :math:`\mathcal{U}_{a, b}` is the uniform distribution between :math:`a` and :math:`b`.

    The parameters of this distribution are:
        p0: The probability of the first gaussian lobe, must be 0 <= p0 <= 1.
        p1: The probability of the second gaussian lobe, must be 0 <= p1 <= 1 and p0 + p1 <= 1.
        μ0: The mean of the first gaussian lobe.
        μ1: The mean of the second gaussian lobe, must be μ0 <= μ1.
        σ0: The standard deviation of the first gaussian lobe, must be σ0 > 0.
        σ1: The standard deviation of the second gaussian lobe, must be σ1 > 0.
        s: The smoothness of the bridge, must be s > 0.
    """

    def pdf(self, x, p0, p1, μ0, μ1, σ0, σ1, s):
        return super().pdf(x, p0, p1, μ0, μ1, σ0, σ1, s)

    def _pdf(
        self,
        x,
        p0: float,
        p1: float,
        μ0: float,
        μ1: float,
        σ0: float,
        σ1: float,
        s: float,
    ):
        return (
            self.lower_lobe_contribution(x, p0, p1, μ0, μ1, σ0, σ1, s)
            + self.upper_lobe_contribution(x, p0, p1, μ0, μ1, σ0, σ1, s)
            + self.plateau_contribution(x, p0, p1, μ0, μ1, σ0, σ1, s)
        )

    def _argcheck(
        self,
        no_atom_probability: float,
        one_atom_probability: float,
        no_atom_mean_signal: float,
        one_atom_mean_signal: float,
        no_atom_noise: float,
        one_atom_noise: float,
        s: float,
    ):
        return (
            (0 <= no_atom_probability <= 1)
            and (0 <= one_atom_probability <= 1)
            and (no_atom_probability + one_atom_probability <= 1)
            and (no_atom_mean_signal < one_atom_mean_signal)
            and (0 < no_atom_noise)
            and (0 < one_atom_noise)
            and (0 < s)
        )

    def plateau_contribution(self, x, p0, p1, μ0, μ1, σ0, σ1, s):
        return self.loss_probability(
            p0, p1, μ0, μ1, σ0, σ1, s
        ) * PlateauDistribution().pdf(x, a=μ0, b=μ1, σ=s)

    def loss_probability(self, p0, p1, μ0, μ1, σ0, σ1, s):
        return 1 - p0 - p1

    def lower_lobe_contribution(self, x, p0, p1, μ0, μ1, σ0, σ1, s):
        return p0 * norm(loc=μ0, scale=σ0).pdf(x)

    def upper_lobe_contribution(self, x, p0, p1, μ0, μ1, σ0, σ1, s):
        return p1 * norm(loc=μ1, scale=σ1).pdf(x)

    def probability_true_positive_no_loss(self, threshold, p0, p1, μ0, μ1, σ0, σ1, s):
        return p1 * (1 - norm.cdf(threshold, μ1, σ1))

    def probability_true_negative(self, threshold, p0, p1, μ0, μ1, σ0, σ1, s):
        return p0 * norm.cdf(threshold, μ0, σ0)

    def probability_true_positive_with_loss(self, threshold, p0, p1, μ0, μ1, σ0, σ1, s):
        return self.probability_true_positive_no_loss(
            threshold, p0, p1, μ0, μ1, σ0, σ1, s
        ) + self.loss_probability(
            p0, p1, μ0, μ1, σ0, σ1, s
        ) * PlateauDistribution().cdf(
            threshold, a=μ0, b=μ1, σ=s
        )

    def probability_perfect_imaging_no_loss(self, threshold, p0, p1, μ0, μ1, σ0, σ1, s):
        return self.probability_true_positive_no_loss(
            threshold, p0, p1, μ0, μ1, σ0, σ1, s
        ) + self.probability_true_negative(threshold, p0, p1, μ0, μ1, σ0, σ1, s)

    def probability_perfect_imaging_with_loss(
        self, threshold, p0, p1, μ0, μ1, σ0, σ1, s
    ):
        return self.probability_true_positive_with_loss(
            threshold, p0, p1, μ0, μ1, σ0, σ1, s
        ) + self.probability_true_negative(threshold, p0, p1, μ0, μ1, σ0, σ1, s)


_constraint_matrix = np.array(
    [
        [1, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0],
        [1, 1, 0, 0, 0, 0, 0],
        [0, 0, -1, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 1],
    ]
)

_lossy_lower_bound = np.array([0, 0, -np.inf, 0, 0, 0, 0])

# for non-lossy, we force p0 + p1 = 1
_non_lossy_lower_bound = np.array([0, 0, 0.99, 0, 0, 0, 0])

_upper_bound = np.array([1, 1, 1, +np.inf, +np.inf, +np.inf, +np.inf])
lossy_bimodal_constraint = LinearConstraint(
    _constraint_matrix, _lossy_lower_bound, _upper_bound, keep_feasible=True
)

non_lossy_bimodal_constraint = LinearConstraint(
    _constraint_matrix, _non_lossy_lower_bound, _upper_bound, keep_feasible=True
)


# noinspection NonAsciiCharacters
class PlateauDistribution(rv_continuous):
    def _pdf(self, x, /, a: float, b: float, σ: float):
        u = (x - a) / np.sqrt(2) / σ
        v = (x - b) / np.sqrt(2) / σ
        return 1 / 2 / (b - a) * (erf(u) - erf(v))

    def _argcheck(self, a: float, b: float, σ: float):
        return np.all(a < b) and σ > 0
