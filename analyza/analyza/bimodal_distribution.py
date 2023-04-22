from scipy.stats import norm


def bimodal_distribution(x, p0, μ0, σ0, μ1, σ1):
    p1 = 1 - p0
    return p0 * norm(μ0, σ0).pdf(x) + p1 * norm(μ1, σ1).pdf(x)


def proba_true_detection(s, p0, μ0, σ0, μ1, σ1):
    return (1 - p0) * (1 - norm.cdf(s, μ1, σ1))


def proba_true_absence(s, p0, μ0, σ0, μ1, σ1):
    return p0 * norm.cdf(s, μ0, σ0)


def proba_false_detection(s, p0, μ0, σ0, μ1, σ1):
    return p0 * (1 - norm.cdf(s, μ0, σ0))


def proba_false_absence(s, p0, μ0, σ0, μ1, σ1):
    return (1 - p0) * norm.cdf(s, μ1, σ1)


def error(s, p0, μ0, σ0, μ1, σ1):
    return proba_false_detection(s, p0, μ0, σ0, μ1, σ1) + proba_false_absence(
        s, p0, μ0, σ0, μ1, σ1
    )
