"""
Early-Warning Signals: Critical Slowing Down and Rate-Induced Tipping

A system approaching a tipping point recovers from perturbations more and
more slowly. That slowing is visible in any monitored series *before* the
transition itself, as two generic statistical fingerprints:

    - lag-1 autocorrelation alpha -> 1
    - variance sigma^2 = sigma_eps^2 / (1 - alpha^2) -> rises

This is the best-calibrated generic early-warning indicator in the
literature (Scheffer et al. 2009, Nature 461:53; Dakos et al. 2012,
PLoS ONE 7:e41010). It has been measured decades ahead of real
transitions: rising AR(1) across >75% of the Amazon basin (Boulton et al.
2022, Nature Climate Change), and the AMOC estimate of 2057 [2025-2095]
(Ditlevsen & Ditlevsen 2023, Nature Communications 14:4254).

HONEST LIMIT: the 2024 meta-analysis (Dakos et al., Nature Ecology &
Evolution) puts generic-EWS detection at ~67.8%. Roughly a third of real
transitions show no advance warning at all. Absence of signal is NOT
evidence of safety, and this module says so in its own output.

SECOND FAILURE MODE: interdependent networks jump discontinuously
(Buldyrev et al. 2010, Nature 464:1025) — a first-order transition offers
no gradient to detect. And rate-induced tipping (Ashwin et al. 2012,
Phil. Trans. R. Soc. A 370:1166) can tip a system whose M(S) is still
positive, purely because forcing outpaces its recovery rate. Both are
reported here as separate channels, because critical slowing down cannot
see either one.

MEASURED OPERATING CHARACTERISTICS
----------------------------------
This module's own flags were measured on synthetic series with a known
answer — 20 stationary AR(1) series that are not approaching anything,
and 20 whose recovery rate erodes from alpha 0.10 to 0.95. At default
settings (window = half the series, 100 surrogates, p <= 0.05):

    stationary series -> any flag raised:   ~8%   (joint: ~0%)
    eroding series    -> any flag raised:  ~75%   (joint: ~8%)

Two things follow. PARTIAL_SIGNAL is the workhorse detection state, not a
near-miss: most genuine erosion shows up in one indicator, not both.
CRITICAL_SLOWING_DOWN is the high-confidence state and is correspondingly
rare. And ~25% of genuinely eroding systems raise nothing at all, which
is the same order as the ~32% miss rate reported for real transitions.

These numbers are reproducible: see tests/test_early_warning.py, which
pins them.

MEASUREMENT, NOT CONTROL
------------------------
This module REPORTS statistical properties of a series. It does not:
  - Recommend interventions
  - Optimize toward a target
  - Predict a date with authority

Every number is reproducible from the input series: surrogate generation
is explicitly seeded, so the same series always yields the same p-values.
Standard library only.
"""

import random
from dataclasses import dataclass, field
from math import log, sqrt
from typing import List, Optional, Sequence

# Minimum points before an autocorrelation estimate means anything.
# Below this the estimator's own variance swamps the signal.
MIN_POINTS_AR1 = 5

# Minimum number of rolling windows before a trend statistic is reported.
MIN_WINDOWS_TREND = 4

# Kendall tau above which an indicator counts as "consistently rising".
# Convention from the EWS literature: tau is reported, not thresholded,
# but a default is needed for a machine-readable flag.
TAU_RISING = 0.5

# A bare tau threshold is not a test. Rolling windows overlap, so the
# indicator series is strongly autocorrelated and |tau| >= 0.5 arises by
# chance in a large fraction of perfectly stationary series. Observed tau
# is therefore compared against a null distribution built from surrogate
# series with the same fitted AR(1) structure and no trend in recovery
# rate (Dakos et al. 2012, PLoS ONE 7:e41010).
# 100 surrogates is the smallest count that reproduces the same flags as
# 200 on the module's own demo series; 50 under-samples the null and
# inflates p enough to lose real detections.
SURROGATE_COUNT = 100
SIGNIFICANCE_P = 0.05

# Surrogates need randomness, and a reading must stay reproducible from
# its inputs. The generator is seeded explicitly and the seed is part of
# the method, not hidden state.
SURROGATE_SEED = 0

# Detection rate of generic EWS in the 2024 meta-analysis. Carried in the
# output so no consumer can read a quiet result as a clean bill of health.
GENERIC_EWS_DETECTION_RATE = 0.678


@dataclass
class EarlyWarningReading:
    """Statistical early-warning state of a monitored series."""

    flag: str                              # CRITICAL_SLOWING_DOWN | PARTIAL_SIGNAL
    #                                        NO_SIGNAL | INSUFFICIENT_DATA
    lag1_autocorrelation: Optional[float]  # alpha over the full series
    variance: Optional[float]              # variance of the full series
    return_time: Optional[float]           # T_r = -dt / ln(alpha), periods
    ar1_trend_tau: Optional[float]         # Kendall tau of rolling AR(1)
    variance_trend_tau: Optional[float]    # Kendall tau of rolling variance
    ar1_p_value: Optional[float] = None    # P(tau this high | no trend)
    variance_p_value: Optional[float] = None
    n_points: int = 0
    n_windows: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class RateTippingReading:
    """Comparison of forcing rate against system recovery rate."""

    flag: str                    # RATE_TIPPING_RISK | WITHIN_TRACKING_CAPACITY
    #                              | INSUFFICIENT_DATA
    forcing_rate: Optional[float]     # mean |d(forcing)/dt| per period
    peak_forcing_rate: Optional[float]  # max |d(forcing)/dt| per period
    recovery_rate: float              # A, the system's tracking capacity
    margin: Optional[float]           # recovery_rate - forcing_rate
    warnings: List[str] = field(default_factory=list)


# --- Basic statistics (stdlib only) --------------------------------------


def mean(series: Sequence[float]) -> float:
    """Arithmetic mean. Raises on an empty series."""
    if not series:
        raise ValueError("mean of empty series")
    return sum(series) / len(series)


def variance(series: Sequence[float]) -> Optional[float]:
    """Sample variance (n-1 denominator). None if fewer than two points."""
    n = len(series)
    if n < 2:
        return None
    mu = mean(series)
    return sum((x - mu) ** 2 for x in series) / (n - 1)


def linear_detrend(series: Sequence[float]) -> List[float]:
    """Remove the least-squares linear trend, returning residuals.

    A rising trend inflates lag-1 autocorrelation on its own; detrending
    first is standard practice in the EWS literature so that a measured
    alpha reflects recovery dynamics rather than the trend.
    """
    n = len(series)
    if n < 2:
        return list(series)
    xs = list(range(n))
    x_bar = mean(xs)
    y_bar = mean(series)
    denom = sum((x - x_bar) ** 2 for x in xs)
    if denom == 0:
        return [y - y_bar for y in series]
    slope = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, series)) / denom
    intercept = y_bar - slope * x_bar
    return [y - (slope * x + intercept) for x, y in zip(xs, series)]


def lag1_autocorrelation(series: Sequence[float], detrend: bool = True) -> Optional[float]:
    """Estimate the AR(1) coefficient alpha of a series.

    alpha is the correlation between the series and itself shifted by one
    period. As a system approaches a tipping point its perturbations decay
    more slowly, so alpha climbs toward 1.

    Args:
        series: Observations, oldest first.
        detrend: Remove the linear trend first (default True).

    Returns:
        alpha, or None if the series is too short or perfectly flat
        (a constant series has no variance and therefore no defined
        autocorrelation).
    """
    if len(series) < MIN_POINTS_AR1:
        return None
    x = linear_detrend(series) if detrend else list(series)
    mu = mean(x)
    centered = [v - mu for v in x]
    denom = sum(v * v for v in centered)
    if denom <= 0:
        return None
    numer = sum(centered[i] * centered[i + 1] for i in range(len(centered) - 1))
    return numer / denom


def return_time(alpha: Optional[float], dt: float = 1.0) -> Optional[float]:
    """Characteristic recovery time T_r from an AR(1) coefficient.

    For x_{t+dt} = alpha * x_t + noise, the underlying eigenvalue is
    lambda = ln(alpha) / dt, and the return time is T_r = 1 / |lambda|.
    As alpha -> 1, lambda -> 0 and T_r diverges: this divergence *is*
    critical slowing down.

    Returns None when alpha is unavailable, non-positive (no exponential
    decay to speak of), or >= 1 (no recovery — the perturbation does not
    decay at all).
    """
    if alpha is None or alpha <= 0.0 or alpha >= 1.0:
        return None
    lam = log(alpha) / dt
    return 1.0 / abs(lam)


def kendall_tau(series: Sequence[float]) -> Optional[float]:
    """Kendall rank correlation (tau-b) of a series against time.

    The EWS convention: the *trend* in a rolling indicator matters more
    than its level, and a rank statistic avoids assuming linearity.
    tau = +1 is a strictly rising indicator, -1 strictly falling.

    Returns None for series shorter than two points or with no
    untied pairs.
    """
    n = len(series)
    if n < 2:
        return None
    concordant = discordant = ties_y = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            dy = series[j] - series[i]
            # x is the time index, always strictly increasing: no x ties
            if dy > 0:
                concordant += 1
            elif dy < 0:
                discordant += 1
            else:
                ties_y += 1
    n0 = n * (n - 1) / 2
    denom = sqrt((n0 - 0) * (n0 - ties_y))
    if denom <= 0:
        return None
    return (concordant - discordant) / denom


def rolling(series: Sequence[float], window: int) -> List[List[float]]:
    """Split a series into overlapping windows of fixed width, oldest first."""
    if window < 2 or len(series) < window:
        return []
    return [list(series[i:i + window]) for i in range(len(series) - window + 1)]


def ar1_surrogates(
    series: Sequence[float],
    count: int = SURROGATE_COUNT,
    seed: int = SURROGATE_SEED,
) -> List[List[float]]:
    """Generate stationary AR(1) surrogates matching a series' structure.

    Each surrogate has the same length, the same fitted lag-1
    autocorrelation and the same residual scale as the original, but a
    *constant* recovery rate by construction — no critical slowing down.
    The distribution of trend statistics across surrogates is therefore
    the null distribution: what tau looks like when nothing is happening.

    Args:
        series: Observations, oldest first.
        count: Number of surrogates.
        seed: Seed for the generator, so the null is reproducible.

    Returns:
        List of surrogate series. Empty if the series has no usable AR(1)
        fit (too short, flat, or non-decaying).
    """
    alpha = lag1_autocorrelation(series)
    if alpha is None or alpha >= 1.0:
        return []
    alpha = max(0.0, alpha)
    detrended = linear_detrend(series)
    var = variance(detrended)
    if var is None or var <= 0:
        return []
    # For a stationary AR(1), var = sigma_eps^2 / (1 - alpha^2).
    sigma_eps = sqrt(max(1e-18, var * (1.0 - alpha ** 2)))

    rng = random.Random(seed)
    n = len(series)
    out: List[List[float]] = []
    for _ in range(count):
        surrogate: List[float] = []
        x = rng.gauss(0.0, sqrt(var))  # start from the stationary distribution
        for _ in range(n):
            x = alpha * x + rng.gauss(0.0, sigma_eps)
            surrogate.append(x)
        out.append(surrogate)
    return out


def _indicator_taus(windows: Sequence[Sequence[float]]) -> tuple:
    """Kendall tau of rolling AR(1) and rolling variance, as a pair."""
    ar1_series = [a for a in (lag1_autocorrelation(w) for w in windows) if a is not None]
    var_series = [v for v in (variance(w) for w in windows) if v is not None]
    ar1_tau = kendall_tau(ar1_series) if len(ar1_series) >= MIN_WINDOWS_TREND else None
    var_tau = kendall_tau(var_series) if len(var_series) >= MIN_WINDOWS_TREND else None
    return ar1_tau, var_tau


def tau_significance(
    series: Sequence[float],
    window: int,
    observed_ar1_tau: Optional[float],
    observed_variance_tau: Optional[float],
    count: int = SURROGATE_COUNT,
    seed: int = SURROGATE_SEED,
) -> tuple:
    """One-sided p-values for observed trend statistics against the null.

    p is the fraction of surrogate series whose tau is at least as high as
    the observed one. Small p means a rising indicator that stationary
    noise rarely produces; large p means the trend is unremarkable.

    Returns:
        (p_ar1, p_variance), either of which is None when the
        corresponding tau or the surrogate fit is unavailable.
    """
    if observed_ar1_tau is None and observed_variance_tau is None:
        return None, None
    surrogates = ar1_surrogates(series, count=count, seed=seed)
    if not surrogates:
        return None, None

    ar1_hits = var_hits = 0
    ar1_total = var_total = 0
    for s in surrogates:
        s_ar1_tau, s_var_tau = _indicator_taus(rolling(s, window))
        if observed_ar1_tau is not None and s_ar1_tau is not None:
            ar1_total += 1
            if s_ar1_tau >= observed_ar1_tau:
                ar1_hits += 1
        if observed_variance_tau is not None and s_var_tau is not None:
            var_total += 1
            if s_var_tau >= observed_variance_tau:
                var_hits += 1

    # (hits + 1) / (total + 1): a p-value of exactly zero would claim more
    # resolution than the number of surrogates can support.
    p_ar1 = ((ar1_hits + 1) / (ar1_total + 1)) if ar1_total else None
    p_var = ((var_hits + 1) / (var_total + 1)) if var_total else None
    return p_ar1, p_var


def default_window(n_points: int) -> int:
    """Window width used when none is supplied: half the series.

    Half-length is the common default in EWS toolkits — long enough for a
    stable estimate, short enough to leave several windows for a trend.
    """
    return max(MIN_POINTS_AR1, n_points // 2)


# --- Composite readings ---------------------------------------------------


def critical_slowing_down(
    series: Sequence[float],
    window: Optional[int] = None,
    dt: float = 1.0,
    tau_threshold: float = TAU_RISING,
    significance: bool = True,
    surrogates: int = SURROGATE_COUNT,
    seed: int = SURROGATE_SEED,
) -> EarlyWarningReading:
    """Scan a monitored series for the critical-slowing-down fingerprint.

    Computes lag-1 autocorrelation and variance in a rolling window, then
    the Kendall tau trend of each. A rising trend in *both* is the
    classical signature (Scheffer 2009; Dakos 2012).

    An indicator counts as rising only if its tau clears `tau_threshold`
    *and* is unlikely under the surrogate null. Without the significance
    test a bare threshold flags roughly two stationary series in five,
    because overlapping windows make the indicator series autocorrelated.

    Args:
        series: Observations, oldest first. May be M(S) history or any
                raw monitored variable feeding it.
        window: Rolling window width. Defaults to half the series length.
        dt: Time between observations, for the return-time conversion.
        tau_threshold: Kendall tau above which an indicator may count as
                       consistently rising.
        significance: Test observed tau against AR(1) surrogates. Turning
                      this off restores the raw-threshold behaviour and
                      its false-alarm rate.
        surrogates: Number of surrogate series in the null distribution.
        seed: Seed for surrogate generation, keeping readings reproducible.

    Returns:
        EarlyWarningReading. flag is INSUFFICIENT_DATA when the series is
        too short to say anything — which is a statement about the data,
        not about the system.
    """
    n = len(series)
    warnings: List[str] = []

    if n < MIN_POINTS_AR1:
        return EarlyWarningReading(
            flag="INSUFFICIENT_DATA",
            lag1_autocorrelation=None,
            variance=None,
            return_time=None,
            ar1_trend_tau=None,
            variance_trend_tau=None,
            n_points=n,
            warnings=[
                f"series has {n} points; at least {MIN_POINTS_AR1} are needed "
                "for a lag-1 estimate. No statement about system state is implied."
            ],
        )

    alpha = lag1_autocorrelation(series)
    var_full = variance(series)
    t_r = return_time(alpha, dt)

    win = window if window is not None else default_window(n)
    windows = rolling(series, win)

    ar1_tau, var_tau = _indicator_taus(windows)

    p_ar1 = p_var = None
    if significance and (ar1_tau is not None or var_tau is not None):
        p_ar1, p_var = tau_significance(
            series, win, ar1_tau, var_tau, count=surrogates, seed=seed
        )
        if p_ar1 is None and p_var is None:
            warnings.append(
                "surrogate null could not be built (no usable AR(1) fit); "
                "trend statistics are reported without a significance test"
            )

    def _rising(tau: Optional[float], p: Optional[float]) -> bool:
        if tau is None or tau < tau_threshold:
            return False
        if significance and p is not None:
            return p <= SIGNIFICANCE_P
        return True

    if ar1_tau is None and var_tau is None:
        flag = "INSUFFICIENT_DATA"
        warnings.append(
            f"only {len(windows)} rolling windows available; "
            f"{MIN_WINDOWS_TREND} are needed for a trend statistic."
        )
    else:
        ar1_rising = _rising(ar1_tau, p_ar1)
        var_rising = _rising(var_tau, p_var)
        if ar1_rising and var_rising:
            flag = "CRITICAL_SLOWING_DOWN"
        elif ar1_rising or var_rising:
            flag = "PARTIAL_SIGNAL"
        else:
            flag = "NO_SIGNAL"

    if flag == "CRITICAL_SLOWING_DOWN":
        warnings.append(
            f"autocorrelation and variance are both rising "
            f"(tau_AR1 = {ar1_tau:.2f}, tau_var = {var_tau:.2f}) — "
            "the system is recovering from perturbations more slowly over time"
        )
    elif flag == "PARTIAL_SIGNAL":
        warnings.append(
            "one of the two indicators is rising but not the other — "
            "weaker evidence than a joint signal; check for a trend or "
            "measurement artifact in the raw series. This is not evidence "
            "of safety either."
        )
    elif flag == "NO_SIGNAL":
        warnings.append(
            "no critical-slowing-down signature detected. Generic early "
            f"warnings catch roughly {GENERIC_EWS_DETECTION_RATE:.0%} of real "
            "transitions (Dakos 2024) — absence of signal is not evidence "
            "of safety, and abrupt first-order transitions in coupled "
            "systems produce no gradient at all."
        )

    if alpha is not None and alpha >= 0.95:
        warnings.append(
            f"lag-1 autocorrelation = {alpha:.3f} is near 1 — perturbations "
            "are barely decaying; recovery capacity is close to exhausted"
        )

    return EarlyWarningReading(
        flag=flag,
        lag1_autocorrelation=alpha,
        variance=var_full,
        return_time=t_r,
        ar1_trend_tau=ar1_tau,
        variance_trend_tau=var_tau,
        ar1_p_value=p_ar1,
        variance_p_value=p_var,
        n_points=n,
        n_windows=len(windows),
        warnings=warnings,
    )


def rate_induced_tipping(
    forcing: Sequence[float],
    adaptability: float,
    dt: float = 1.0,
) -> RateTippingReading:
    """Compare the rate of external forcing against the system's recovery rate.

    Rate-induced tipping (Ashwin et al. 2012) is the failure mode that a
    static M(S) cannot see: a system can hold a positive coherence reading
    and still tip, purely because the environment is moving faster than the
    system can track it. The comparison is between d(forcing)/dt and the
    adaptability term A, which is exactly a recovery rate.

    Args:
        forcing: External driver series, oldest first, in the same units
                 as adaptability so the comparison is meaningful.
        adaptability: A, the system's recovery rate per period.
        dt: Time between forcing observations.

    Returns:
        RateTippingReading. RATE_TIPPING_RISK when mean or peak forcing
        rate meets or exceeds A — the system cannot track its own
        equilibrium, regardless of where M(S) currently sits.
    """
    warnings: List[str] = []

    if len(forcing) < 2:
        return RateTippingReading(
            flag="INSUFFICIENT_DATA",
            forcing_rate=None,
            peak_forcing_rate=None,
            recovery_rate=adaptability,
            margin=None,
            warnings=["forcing series needs at least two points to give a rate"],
        )

    rates = [abs(b - a) / dt for a, b in zip(forcing[:-1], forcing[1:])]
    mean_rate = mean(rates)
    peak_rate = max(rates)
    margin = adaptability - mean_rate

    if adaptability <= 0:
        flag = "RATE_TIPPING_RISK"
        warnings.append(
            "adaptability is zero or negative — the system has no capacity "
            "to track any forcing at all"
        )
    elif mean_rate >= adaptability or peak_rate >= adaptability:
        flag = "RATE_TIPPING_RISK"
        warnings.append(
            f"forcing rate (mean {mean_rate:.3f}, peak {peak_rate:.3f}) meets or "
            f"exceeds recovery rate A = {adaptability:.3f} — the system cannot "
            "track its moving equilibrium. Rate-induced tipping is possible "
            "while M(S) is still positive (Ashwin 2012)."
        )
    else:
        flag = "WITHIN_TRACKING_CAPACITY"
        warnings.append(
            f"forcing rate {mean_rate:.3f} is below recovery rate "
            f"{adaptability:.3f}; margin {margin:.3f}"
        )

    return RateTippingReading(
        flag=flag,
        forcing_rate=mean_rate,
        peak_forcing_rate=peak_rate,
        recovery_rate=adaptability,
        margin=margin,
        warnings=warnings,
    )


def format_reading(r: EarlyWarningReading) -> str:
    """Human-readable rendering of an EarlyWarningReading."""

    def num(value: Optional[float], fmt: str = "{:+.4f}") -> str:
        return "n/a" if value is None else fmt.format(value)

    lines = [
        "=" * 70,
        f"EARLY WARNING: {r.flag}",
        "=" * 70,
        f"  points / windows = {r.n_points} / {r.n_windows}",
        f"  lag-1 AR(1)      = {num(r.lag1_autocorrelation)}",
        f"  variance         = {num(r.variance)}",
        f"  return time      = {num(r.return_time, '{:.2f}')} periods",
        f"  tau (AR(1))      = {num(r.ar1_trend_tau)}   p = {num(r.ar1_p_value, '{:.3f}')}",
        f"  tau (variance)   = {num(r.variance_trend_tau)}   p = {num(r.variance_p_value, '{:.3f}')}",
    ]
    if r.warnings:
        lines.append("")
        lines.append("NOTES:")
        for w in r.warnings:
            lines.append(f"  - {w}")
    lines.extend([
        "",
        "This is a reading, not a prescription. Decide what it means for you.",
        "=" * 70,
    ])
    return "\n".join(lines)


# Demo
if __name__ == "__main__":
    import random

    random.seed(7)

    # A system whose recovery rate erodes: alpha climbs 0.10 -> 0.95.
    approaching = []
    x = 0.0
    for step in range(120):
        alpha_t = 0.10 + 0.85 * (step / 119)
        x = alpha_t * x + random.gauss(0, 0.1)
        approaching.append(x)

    # A stable system: alpha fixed and low throughout.
    stable = []
    x = 0.0
    for _ in range(120):
        x = 0.2 * x + random.gauss(0, 0.1)
        stable.append(x)

    print(format_reading(critical_slowing_down(approaching)))
    print()
    print(format_reading(critical_slowing_down(stable)))
    print()

    # Forcing that outruns a slow system's recovery rate.
    forcing = [0.05 * t for t in range(20)]
    reading = rate_induced_tipping(forcing, adaptability=0.03)
    print("=" * 70)
    print(f"RATE TIPPING: {reading.flag}")
    print("=" * 70)
    for w in reading.warnings:
        print(f"  - {w}")
    print("=" * 70)
