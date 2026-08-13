"""
Calibration Adapters: from measured data to M(S) inputs

Until now every term in M(S) = (R_e x A x D x f(C)) - L has been a raw
float supplied by whoever ran the model. That is honest but unfalsifiable:
two people measuring the same system can hand the formula different
numbers and neither can be shown wrong.

This module closes that gap. Each adapter is a *named, cited* derivation
of one M(S) term from data somebody actually measured, and each returns
the citation and its caveats alongside the number. If you disagree with a
calibration, you now have something specific to disagree with.

WHAT THIS IS NOT
----------------
These are not the only valid calibrations, and none of them is
authoritative. They are worked examples showing that the terms *can* be
grounded, with the derivation exposed. A community measuring itself is
free to substitute its own adapters — that is the point of publishing the
derivation rather than the number.

MEASUREMENT, NOT CONTROL
------------------------
An adapter converts observations into a reading. It does not set targets,
and no adapter should ever be inverted to ask "what data would give me the
M(S) I want" — that is Goodhart's law with extra steps (Manheim &
Garrabrant 2018, arXiv:1803.04585; Campbell 1979).

Standard library only.
"""

from dataclasses import dataclass, field
from math import exp, log, sqrt
from typing import Dict, List, Optional, Sequence

# Hormesis: adaptive capacity under mild stress tops out at roughly
# 1.3-1.6x baseline across a very large toxicological literature
# (Calabrese & Baldwin 2002, Nature 421:691). Adaptability is bounded
# plasticity, not a free parameter.
HORMESIS_MAX_GAIN = 1.6

# ATP as a fraction of baseline below which cells switch to death mode
# (Lieberthal et al. 1998, Am J Physiol 274:F315, PMID 9486226). Used as
# the shape of a hard energy floor: below the floor there is no partial
# credit, and between floor and ceiling the response is steep.
ATP_DEATH_FLOOR = 0.15
ATP_RECOVERY_CEILING = 0.25

# Interdependent networks fail at a much higher occupation probability
# than isolated ones: p_c = 2.4554/<k> versus 1/<k> (Buldyrev et al. 2010,
# Nature 464:1025). The ratio is the cost of coupling two networks.
BULDYREV_COEFFICIENT = 2.4554


@dataclass
class Calibration:
    """One M(S) input derived from measured data, with its provenance."""

    term: str                 # R_e | A | D | L | f(C)
    value: float              # the calibrated number
    source: str               # citation for the derivation
    method: str               # what was computed, in one line
    inputs: Dict[str, float] = field(default_factory=dict)
    caveats: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"{self.term} = {self.value:.4f}  ({self.method})", f"  source: {self.source}"]
        for c in self.caveats:
            lines.append(f"  caveat: {c}")
        return "\n".join(lines)


def _clamp01(x: float) -> float:
    """Constrain a value to [0, 1]. M(S) terms are defined on that interval."""
    return max(0.0, min(1.0, x))


def _mean(series: Sequence[float]) -> float:
    if not series:
        raise ValueError("mean of empty series")
    return sum(series) / len(series)


def _variance(series: Sequence[float]) -> float:
    n = len(series)
    if n < 2:
        return 0.0
    mu = _mean(series)
    return sum((x - mu) ** 2 for x in series) / (n - 1)


# --- R_e: resonance energy -----------------------------------------------


def R_e_from_aerobic_scope(
    max_metabolic_rate: float,
    standard_metabolic_rate: float,
    reference_scope: Optional[float] = None,
) -> Calibration:
    """Usable-energy headroom as aerobic scope, AS = MMR - SMR.

    Oxygen- and capacity-limited thermal tolerance (Pörtner & Knust 2007,
    Science 315:95) gives the cleanest empirical analogue of R_e: the
    energy available for anything beyond staying alive. It falls to zero
    at the critical temperature, and the organism's collapse follows.
    A system whose entire throughput services its own maintenance has
    R_e = 0 by construction.

    Args:
        max_metabolic_rate: Total sustainable throughput (MMR).
        standard_metabolic_rate: Throughput consumed by maintenance (SMR).
        reference_scope: Scope at the system's unstressed baseline, used
                         to normalize. Defaults to MMR, giving the
                         fraction of capacity that is discretionary.

    Returns:
        Calibration for R_e in [0, 1].
    """
    scope = max_metabolic_rate - standard_metabolic_rate
    ref = reference_scope if reference_scope is not None else max_metabolic_rate
    value = _clamp01(scope / ref) if ref > 0 else 0.0
    caveats = [
        "aerobic scope is a rate, not a stock — a system can hold positive "
        "scope and still fail from a depleted reserve",
    ]
    if scope <= 0:
        caveats.append(
            "scope is zero or negative: maintenance consumes the entire "
            "throughput. This is the T_crit condition, and M(S) will read "
            "BLACK on R_e."
        )
    return Calibration(
        term="R_e",
        value=value,
        source="Pörtner & Knust 2007, Science 315:95 (OCLTT)",
        method="aerobic scope (MMR - SMR) normalized against reference scope",
        inputs={
            "max_metabolic_rate": max_metabolic_rate,
            "standard_metabolic_rate": standard_metabolic_rate,
            "reference_scope": ref,
        },
        caveats=caveats,
    )


def R_e_from_energy_floor(available_fraction: float) -> Calibration:
    """Constructive-energy availability against a hard floor.

    Below ~15% of baseline ATP, cells stop attempting repair and switch to
    death mode; recovery is reliable only above ~25% (Lieberthal 1998).
    The shape matters more than the biology: many systems have a floor
    below which remaining energy buys no restoration at all, so a linear
    reading of "energy available" overstates health near the bottom.

    Args:
        available_fraction: Energy available as a fraction of baseline.

    Returns:
        Calibration for R_e in [0, 1], zero at or below the death floor.
    """
    f = max(0.0, available_fraction)
    if f <= ATP_DEATH_FLOOR:
        value = 0.0
    elif f >= ATP_RECOVERY_CEILING:
        value = _clamp01(f)
    else:
        # steep transition band: no partial credit is earned linearly here
        span = ATP_RECOVERY_CEILING - ATP_DEATH_FLOOR
        value = _clamp01(ATP_RECOVERY_CEILING * ((f - ATP_DEATH_FLOOR) / span) ** 2)
    return Calibration(
        term="R_e",
        value=value,
        source="Lieberthal et al. 1998, Am J Physiol 274:F315 (PMID 9486226)",
        method=(
            f"available energy fraction with hard floor at {ATP_DEATH_FLOOR:.0%} "
            f"and reliable-recovery ceiling at {ATP_RECOVERY_CEILING:.0%}"
        ),
        inputs={"available_fraction": available_fraction},
        caveats=[
            "the floor is a threshold, not a gradient: readings just above it "
            "are not proportionally safer",
        ],
    )


# --- A: adaptability ------------------------------------------------------


def A_from_timeseries(
    series: Sequence[float],
    dt: float = 1.0,
    reference_rate: Optional[float] = None,
) -> Calibration:
    """Recovery rate measured directly from a monitored series.

    For a system relaxing as x_{t+dt} = alpha * x_t + noise, the recovery
    rate is |lambda| = |ln(alpha)| / dt. This is the same quantity that
    critical-slowing-down theory watches approach zero at a tipping point
    (Scheffer et al. 2009, Nature 461:53), which makes A the one M(S) term
    that a generic early-warning statistic measures directly.

    Args:
        series: Monitored observations, oldest first.
        dt: Time between observations.
        reference_rate: Recovery rate corresponding to A = 1. Defaults to
                        1/dt, i.e. full recovery within one period.

    Returns:
        Calibration for A in [0, 1]. A = 0 when the series shows no decay
        at all (alpha >= 1) — perturbations persist indefinitely.
    """
    from .early_warning import lag1_autocorrelation  # local: avoids a cycle at import

    alpha = lag1_autocorrelation(series)
    ref = reference_rate if reference_rate is not None else 1.0 / dt
    caveats = [
        "assumes the series is dominated by relaxation toward one "
        "equilibrium; a multi-modal or driven series breaks that assumption",
    ]

    if alpha is None:
        rate = 0.0
        caveats.append(
            "autocorrelation undefined (series too short or perfectly flat); "
            "A reported as 0 for lack of evidence, not as a measurement of zero"
        )
    elif alpha >= 1.0:
        rate = 0.0
        caveats.append(
            f"lag-1 autocorrelation = {alpha:.3f} >= 1 — perturbations do not "
            "decay; there is no measurable recovery"
        )
    elif alpha <= 0.0:
        # Anti-correlated: perturbations reverse within a single period.
        rate = ref
        caveats.append(
            f"lag-1 autocorrelation = {alpha:.3f} <= 0 — recovery is faster "
            "than the sampling interval, so A is capped by sample resolution"
        )
    else:
        rate = abs(log(alpha) / dt)

    return Calibration(
        term="A",
        value=_clamp01(rate / ref) if ref > 0 else 0.0,
        source="Scheffer et al. 2009, Nature 461:53; Dakos et al. 2012, PLoS ONE 7:e41010",
        method="recovery rate |ln(alpha)|/dt from lag-1 autocorrelation, normalized",
        inputs={"alpha": alpha if alpha is not None else float("nan"),
                "dt": dt, "reference_rate": ref},
        caveats=caveats,
    )


def A_from_recovery_events(return_times: Sequence[float],
                           reference_time: Optional[float] = None) -> Calibration:
    """Recovery rate from directly observed disturbance-recovery episodes.

    Where a system's recoveries have been timed rather than inferred, the
    recovery rate is simply 1/T_r. This is the more defensible adapter
    when the events are on record: it makes no AR(1) assumption.

    Args:
        return_times: Observed periods taken to return to baseline.
        reference_time: T_r corresponding to A = 1. Defaults to the
                        fastest observed recovery.

    Returns:
        Calibration for A in [0, 1].
    """
    positive = [t for t in return_times if t > 0]
    if not positive:
        return Calibration(
            term="A",
            value=0.0,
            source="Scheffer et al. 2009, Nature 461:53 (return time T_r ~ 1/|lambda|)",
            method="mean observed return time",
            inputs={},
            caveats=[
                "no completed recoveries on record; A = 0 reflects absent "
                "evidence, and a system that has never been observed to "
                "recover is not the same as one observed never to recover",
            ],
        )
    mean_tr = _mean(positive)
    ref = reference_time if reference_time is not None else min(positive)
    return Calibration(
        term="A",
        value=_clamp01(ref / mean_tr),
        source="Scheffer et al. 2009, Nature 461:53 (return time T_r ~ 1/|lambda|)",
        method="fastest observed return time divided by mean return time",
        inputs={"mean_return_time": mean_tr, "reference_time": ref,
                "n_events": float(len(positive))},
        caveats=[
            "survivorship bias: only recoveries that completed are timed, so "
            "the estimate is optimistic for systems that sometimes never return",
        ],
    )


def apply_hormesis_ceiling(baseline_A: float, claimed_gain: float) -> Calibration:
    """Cap a claimed increase in adaptability at the hormetic maximum.

    Mild stress does raise adaptive capacity, but across a very large
    dose-response literature the gain saturates around 1.3-1.6x baseline
    (Calabrese & Baldwin 2002, Nature 421:691). Any model that lets A grow
    without bound will manufacture resilience that does not exist.

    Args:
        baseline_A: Unstressed adaptability.
        claimed_gain: Multiplier some intervention or argument claims.

    Returns:
        Calibration for A, capped at HORMESIS_MAX_GAIN x baseline and at 1.
    """
    capped_gain = min(claimed_gain, HORMESIS_MAX_GAIN)
    caveats = []
    if claimed_gain > HORMESIS_MAX_GAIN:
        caveats.append(
            f"claimed gain {claimed_gain:.2f}x exceeds the hormetic ceiling "
            f"{HORMESIS_MAX_GAIN}x and was capped — adaptive capacity is "
            "bounded plasticity, not a free parameter"
        )
    if claimed_gain < 1.0:
        caveats.append("claimed gain is below 1: this is a loss of adaptability, not hormesis")
    return Calibration(
        term="A",
        value=_clamp01(baseline_A * capped_gain),
        source="Calabrese & Baldwin 2002, Nature 421:691 (hormetic dose-response)",
        method=f"baseline adaptability x gain, capped at {HORMESIS_MAX_GAIN}x",
        inputs={"baseline_A": baseline_A, "claimed_gain": claimed_gain,
                "applied_gain": capped_gain},
        caveats=caveats,
    )


# --- D: diversity ---------------------------------------------------------


def D_response_diversity(responses: Sequence[Sequence[float]]) -> Calibration:
    """Diversity measured as *response* diversity, not richness.

    Counting strategies is the wrong measurement (Elmqvist et al. 2003,
    Front Ecol Environ 1:488): what buys resilience is components that
    respond *differently* to the same stress. Loreau & de Mazancourt
    (2008, Am Nat 172:E48; 2013, Ecol Lett 16:106) give the synchrony
    index

        phi = var(sum of components) / (sum of component sds)^2

    with phi = 1 under perfect synchrony and phi = 1/n for n independent
    components. Effective independent responses is 1/phi, and D is
    reported as 1 - phi: a hundred components that all move together
    score near zero, which is the intended behaviour.

    Args:
        responses: One series per component, each recording that
                   component's response across the same stress gradient.
                   All series must be the same length.

    Returns:
        Calibration for D in [0, 1], carrying effective_n in its inputs.
    """
    n = len(responses)
    if n == 0:
        return Calibration(
            term="D", value=0.0,
            source="Elmqvist et al. 2003, Front Ecol Environ 1:488",
            method="response diversity via Loreau synchrony index",
            inputs={"n_components": 0.0},
            caveats=["no components supplied: no viable strategies to measure"],
        )
    lengths = {len(r) for r in responses}
    if len(lengths) != 1:
        raise ValueError("all response series must cover the same stress gradient")
    if lengths.pop() < 2:
        raise ValueError("each response series needs at least two points")

    sds = [sqrt(_variance(r)) for r in responses]
    total = [sum(r[i] for r in responses) for i in range(len(responses[0]))]
    var_total = _variance(total)
    sum_sd = sum(sds)

    caveats = [
        "measures how differently components respond, which is not how many "
        "there are — a rich but synchronized system scores low, correctly",
    ]

    if sum_sd <= 0:
        # Nothing responds to the stressor at all.
        phi = 1.0
        caveats.append(
            "no component varies across the stress gradient; either the "
            "system is unresponsive or the gradient did not stress it"
        )
    else:
        phi = var_total / (sum_sd ** 2)

    phi = _clamp01(phi)
    effective_n = (1.0 / phi) if phi > 0 else float(n)
    if n == 1:
        caveats.append("a single component cannot have response diversity by construction")

    return Calibration(
        term="D",
        value=_clamp01(1.0 - phi),
        source="Elmqvist et al. 2003, Front Ecol Environ 1:488; "
               "Loreau & de Mazancourt 2013, Ecol Lett 16:106",
        method="1 - synchrony index phi = var(total) / (sum of component sds)^2",
        inputs={"n_components": float(n), "synchrony_phi": phi,
                "effective_independent_responses": effective_n},
        caveats=caveats,
    )


def D_effective_number(proportions: Sequence[float]) -> Calibration:
    """Effective number of strategies from their relative weights.

    The Hill number of order 1, exp(Shannon entropy), normalized by the
    raw count. This is the *richness-and-evenness* reading of diversity —
    weaker than response diversity, and included because it is often the
    only thing on record.

    Args:
        proportions: Relative weight of each viable strategy. Normalized
                     internally if they do not sum to 1.

    Returns:
        Calibration for D in [0, 1].
    """
    weights = [p for p in proportions if p > 0]
    if not weights:
        return Calibration(
            term="D", value=0.0,
            source="Hill 1973, Ecology 54:427; Jost 2006, Oikos 113:363",
            method="exp(Shannon entropy) normalized by strategy count",
            inputs={"n_strategies": 0.0},
            caveats=["no strategies with positive weight: D = 0 is irreversible in M(S)"],
        )
    total = sum(weights)
    ps = [w / total for w in weights]
    shannon = -sum(p * log(p) for p in ps)
    effective = exp(shannon)
    n = len(proportions)
    return Calibration(
        term="D",
        value=_clamp01(effective / n) if n > 0 else 0.0,
        source="Hill 1973, Ecology 54:427; Jost 2006, Oikos 113:363",
        method="exp(Shannon entropy) normalized by strategy count",
        inputs={"n_strategies": float(n), "effective_number": effective},
        caveats=[
            "richness and evenness only — says nothing about whether the "
            "strategies respond differently to stress. Prefer "
            "D_response_diversity when the response data exists.",
        ],
    )


def D_model_collapse(synthetic_fraction: float, accumulate: bool = False) -> Calibration:
    """Diversity of a recursively trained generative system.

    Model collapse is the one domain where M(S)'s mechanism is directly
    observable: train on your own output and the distribution's tails
    vanish first, variance shrinks toward zero, and the process compounds
    (Shumailov et al. 2024, Nature 631:755). Dohmatob et al. 2024 show it
    is a phase transition — a synthetic fraction of order 1% can trigger
    it. Gerstgrasser et al. 2024 show the escape: *accumulating* real data
    alongside synthetic data avoids collapse entirely.

    Args:
        synthetic_fraction: Share of training data that is model-generated.
        accumulate: True if real data is retained and accumulated rather
                    than replaced each generation.

    Returns:
        Calibration for D in [0, 1].
    """
    f = _clamp01(synthetic_fraction)
    caveats = []
    if accumulate:
        # Retained real data holds the tails open regardless of how much
        # synthetic data is layered on top.
        value = _clamp01(1.0 - 0.25 * f)
        caveats.append(
            "accumulation regime: real data retained, so tail loss is bounded "
            "(Gerstgrasser et al. 2024)"
        )
    else:
        # Replacement regime: collapse is a phase transition, not a slope.
        value = _clamp01((1.0 - f) ** 3)
        caveats.append(
            "replacement regime: each generation discards real data, so tail "
            "loss compounds across generations — the exponent here is a shape, "
            "not a fitted constant"
        )
        if f >= 0.01:
            caveats.append(
                f"synthetic fraction {f:.1%} is at or above the ~1% level "
                "reported to trigger the transition (Dohmatob et al. 2024)"
            )
    return Calibration(
        term="D",
        value=value,
        source="Shumailov et al. 2024, Nature 631:755; Dohmatob et al. 2024; "
               "Gerstgrasser et al. 2024",
        method="tail retention under synthetic-data contamination",
        inputs={"synthetic_fraction": f, "accumulate": 1.0 if accumulate else 0.0},
        caveats=caveats,
    )


# --- L: loss / entropy rate ----------------------------------------------


def L_decay_rate(fraction_lost: float, over_periods: float) -> Calibration:
    """Annualized (per-period) loss rate from an observed cumulative loss.

    Converts "we lost X% over N periods" into the exponential rate that
    produced it: lambda = -ln(1 - X) / N. Link rot is the worked example —
    13-22% of referenced URLs are unreachable within two years — but the
    conversion is generic to any measured attrition.

    Args:
        fraction_lost: Cumulative fraction lost, in [0, 1).
        over_periods: Number of periods over which that loss accumulated.

    Returns:
        Calibration for L as a per-period rate.
    """
    if over_periods <= 0:
        raise ValueError("over_periods must be positive")
    f = fraction_lost
    caveats = ["a rate, not a stock: L compounds, so a small rate is not a small loss"]
    if f >= 1.0:
        rate = 1.0
        caveats.append("total loss observed; rate is unbounded and reported as 1.0")
    elif f <= 0.0:
        rate = 0.0
        caveats.append("no loss observed over the window; absence of loss is not permanence")
    else:
        rate = -log(1.0 - f) / over_periods
    return Calibration(
        term="L",
        value=_clamp01(rate),
        source="e.g. link rot 13-22% within 2 years; generic exponential attrition",
        method="lambda = -ln(1 - fraction_lost) / periods",
        inputs={"fraction_lost": f, "over_periods": over_periods},
        caveats=caveats,
    )


def L_knowledge_halflife(half_life_periods: float) -> Calibration:
    """Loss rate implied by a measured knowledge half-life.

    lambda = ln(2) / t_half. Field-specific half-lives are on record —
    roughly 7-13 years for monograph citation — and give an entropy rate
    for stored knowledge that is not a guess.

    Args:
        half_life_periods: Periods over which half the stored knowledge
                           ceases to be current.

    Returns:
        Calibration for L as a per-period rate.
    """
    if half_life_periods <= 0:
        raise ValueError("half_life_periods must be positive")
    return Calibration(
        term="L",
        value=_clamp01(log(2) / half_life_periods),
        source="citation half-life literature (field-specific, ~7-13 yr monograph)",
        method="lambda = ln(2) / half-life",
        inputs={"half_life_periods": half_life_periods},
        caveats=[
            "obsolescence and falsification are different losses; this rate "
            "covers content going stale, not content found to be wrong",
        ],
    )


def L_audited_false_fraction(replication_rate: float) -> Calibration:
    """Loss rate from the audited false fraction of stored knowledge.

    Replication audits give a directly measured number for how much of a
    body of knowledge does not hold: ~36% replicated in psychology
    (Open Science Collaboration 2015, Science 349:aac4716), ~21% in
    preclinical cancer biology (Begley & Ellis 2012, Nature 483:531).
    Unlike obsolescence this is content that was never true, and it does
    not decay on its own.

    Args:
        replication_rate: Fraction of findings that replicated, in [0, 1].

    Returns:
        Calibration for L as a standing loss fraction.
    """
    r = _clamp01(replication_rate)
    return Calibration(
        term="L",
        value=_clamp01(1.0 - r),
        source="Open Science Collaboration 2015, Science 349:aac4716; "
               "Begley & Ellis 2012, Nature 483:531",
        method="1 - replication rate, as a standing false fraction",
        inputs={"replication_rate": r},
        caveats=[
            "a standing fraction, not a rate — it does not decay without an "
            "active correction process, so combining it with rate-type losses "
            "requires stating the period explicitly",
        ],
    )


def L_combined(components: Sequence[Calibration]) -> Calibration:
    """Combine independent per-period loss rates.

    Independent losses compound rather than add: the survival fraction is
    the product of individual survivals, so
    L_total = 1 - prod(1 - L_i). Summing instead overstates the total and
    can exceed 1 with enough small components.

    Args:
        components: Calibrations for L, each a per-period rate.

    Returns:
        Combined Calibration for L.
    """
    if not components:
        return Calibration(
            term="L", value=0.0, source="composition of independent rates",
            method="1 - product of survival fractions",
            inputs={"n_components": 0.0},
            caveats=["no loss channels supplied; L = 0 means unmeasured, not absent"],
        )
    non_L = [c.term for c in components if c.term != "L"]
    if non_L:
        raise ValueError(f"L_combined takes only L calibrations, got: {sorted(set(non_L))}")
    survival = 1.0
    for c in components:
        survival *= (1.0 - _clamp01(c.value))
    return Calibration(
        term="L",
        value=_clamp01(1.0 - survival),
        source="composition of independent rates",
        method="1 - product of survival fractions (independent losses compound)",
        inputs={"n_components": float(len(components))},
        caveats=[
            "assumes the loss channels are independent; correlated losses "
            "(one failure causing another) compound faster than this",
            "sources: " + "; ".join(sorted({c.source for c in components})),
        ],
    )


# --- f(C): coupling bounds ------------------------------------------------


def may_stability_ceiling(
    interaction_sd: float,
    n_components: int,
    connectance: float,
    self_damping: float,
) -> Calibration:
    """May's stability bound on coupling: sigma * sqrt(S*C) < d.

    A randomly assembled system of S components with connectance C and
    interaction strength sd sigma is stable only while
    sigma * sqrt(S*C) < d, the self-damping rate (May 1972, Nature
    238:413). This is a hard quantitative ceiling on how much coupling a
    system of a given size can carry, and it is the clearest reason f(C)
    peaks at an intermediate value rather than rising with connection.

    Args:
        interaction_sd: Standard deviation of interaction strengths.
        n_components: Number of interacting components S.
        connectance: Fraction of possible links realized C, in [0, 1].
        self_damping: Self-regulation rate d.

    Returns:
        Calibration for f(C) in [0, 1] — the ratio of the stability
        margin to the bound, 0 when the bound is breached.
    """
    if self_damping <= 0:
        raise ValueError("self_damping must be positive for the bound to be defined")
    criterion = interaction_sd * sqrt(max(0, n_components) * _clamp01(connectance))
    margin = (self_damping - criterion) / self_damping
    caveats = [
        "derived for randomly assembled interaction matrices; real systems "
        "with structured interactions can be stable past the bound",
    ]
    if criterion >= self_damping:
        caveats.append(
            f"bound breached: sigma*sqrt(SC) = {criterion:.3f} >= d = "
            f"{self_damping:.3f} — coupling exceeds what self-regulation can absorb"
        )
    return Calibration(
        term="f(C)",
        value=_clamp01(margin),
        source="May 1972, Nature 238:413",
        method="stability margin (d - sigma*sqrt(S*C)) / d",
        inputs={"interaction_sd": interaction_sd, "n_components": float(n_components),
                "connectance": connectance, "self_damping": self_damping,
                "criterion": criterion},
        caveats=caveats,
    )


def interdependence_penalty(mean_degree: float, coupled_fraction: float = 1.0) -> Calibration:
    """Fragility added by making two networks interdependent.

    An isolated random network keeps a giant component down to
    p_c = 1/<k>; two interdependent networks fail at p_c = 2.4554/<k>
    (Buldyrev et al. 2010, Nature 464:1025), and the failure is
    first-order — an abrupt jump with no gradient beforehand. Parshani
    et al. 2010 show partial coupling q interpolates between the two.

    The practical consequence for M(S): near this threshold the loss term
    L gives no advance warning, because there is no gradual degradation to
    measure. The multiplicative coherence terms are the leading indicators.

    Args:
        mean_degree: Average node degree <k>.
        coupled_fraction: Fraction of nodes with cross-network dependency,
                          in [0, 1]. Zero recovers the isolated case.

    Returns:
        Calibration for f(C) in [0, 1], with both thresholds in inputs.
    """
    if mean_degree <= 0:
        raise ValueError("mean_degree must be positive")
    q = _clamp01(coupled_fraction)
    isolated_pc = 1.0 / mean_degree
    coupled_pc = BULDYREV_COEFFICIENT / mean_degree
    # Linear interpolation in q between the isolated and fully coupled thresholds.
    effective_pc = isolated_pc + q * (coupled_pc - isolated_pc)
    caveats = [
        "the interdependent transition is first-order: it jumps rather than "
        "slides, so no early-warning gradient precedes it",
    ]
    if q > 0:
        caveats.append(
            f"coupled failure threshold {effective_pc:.3f} vs isolated "
            f"{isolated_pc:.3f} — interdependence costs "
            f"{effective_pc / isolated_pc:.2f}x in tolerated node loss"
        )
    return Calibration(
        term="f(C)",
        value=_clamp01(1.0 - effective_pc),
        source="Buldyrev et al. 2010, Nature 464:1025; Parshani et al. 2010, PRL 105:048701",
        method="1 - percolation threshold interpolated by coupled fraction q",
        inputs={"mean_degree": mean_degree, "coupled_fraction": q,
                "isolated_pc": isolated_pc, "coupled_pc": coupled_pc,
                "effective_pc": effective_pc},
        caveats=caveats,
    )


# Demo
if __name__ == "__main__":
    print("=" * 70)
    print("CALIBRATION ADAPTERS — deriving M(S) inputs from measured data")
    print("=" * 70)
    print()

    readings = [
        R_e_from_aerobic_scope(max_metabolic_rate=100.0, standard_metabolic_rate=62.0),
        R_e_from_energy_floor(available_fraction=0.18),
        A_from_recovery_events([3.0, 4.0, 3.5, 9.0]),
        apply_hormesis_ceiling(baseline_A=0.5, claimed_gain=3.0),
        D_response_diversity([
            [1.0, 0.8, 0.6, 0.4],   # declines under stress
            [1.0, 1.1, 1.3, 1.5],   # benefits from it
            [1.0, 1.0, 0.9, 1.0],   # largely indifferent
        ]),
        D_model_collapse(synthetic_fraction=0.6, accumulate=False),
        D_model_collapse(synthetic_fraction=0.6, accumulate=True),
        L_decay_rate(fraction_lost=0.22, over_periods=2.0),
        L_knowledge_halflife(half_life_periods=9.0),
        may_stability_ceiling(interaction_sd=0.4, n_components=25,
                              connectance=0.3, self_damping=1.0),
        interdependence_penalty(mean_degree=4.0, coupled_fraction=1.0),
    ]

    for r in readings:
        print(r)
        print()

    combined = L_combined([
        L_decay_rate(fraction_lost=0.22, over_periods=2.0),
        L_knowledge_halflife(half_life_periods=9.0),
    ])
    print(combined)
    print()
    print("=" * 70)
    print("Every number above is a derivation you can argue with. That is the point.")
    print("=" * 70)
