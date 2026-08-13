"""
Uncertainty Propagation: what the data actually determines

M(S) = (R_e x A x D x f(C)) - L takes five inputs and returns one number
with no error bar. That number reads as precise. It is not: the
calibration adapters in this package derive their inputs from published
relationships that come with ranges, disagreements and caveats, and the
gain term is a *product*, so relative uncertainties compound rather than
average out.

This module propagates input ranges through the formula and reports what
survives. The decision-relevant output is usually not the width of the
M(S) interval but whether the *verdict* is determined at all: if GREEN
and RED are both reachable from your inputs, the signal you read off a
point estimate was an artifact of the point you chose.

TWO PROPAGATION MODES
---------------------
`propagate` uses interval arithmetic. Because M(S) is monotonically
increasing in R_e, A, D and f(C) and decreasing in L, the extremes sit
exactly at opposite corners of the input box — the bounds are tight and
require no sampling. They are guarantees, not estimates.

`monte_carlo` samples the inputs to get a *distribution*, which interval
arithmetic cannot give: the probability that M(S) is negative, and how
the probability mass splits across signals. This buys resolution at the
cost of two assumptions that intervals do not make — a distribution
shape, and independence between inputs. Both are stated in the output.

INDEPENDENCE IS THE ASSUMPTION MOST LIKELY TO BE WRONG
------------------------------------------------------
Sampling inputs independently understates the tails. Real systems
correlate: the same stress that drains R_e usually also erodes A and D,
so the genuinely bad corner is far more likely than independent sampling
implies. Interval bounds are immune to this — they already contain every
correlation structure — which is why they are the default here.

MEASUREMENT, NOT CONTROL
------------------------
Reporting that a verdict is undetermined is a statement about the
evidence, not permission to pick the reading you prefer. The honest
response to an undetermined verdict is narrower inputs, not a
narrower interval.

Standard library only.
"""

import random
from dataclasses import dataclass, field
from itertools import product
from typing import Dict, List, Optional, Sequence, Tuple

from .coherence_verdict import (
    time_to_collapse,
    trajectory_from_history,
    yield_signal,
)

# The multiplicative terms, in the order used for corner enumeration.
GAIN_TERMS = ("resonance_energy", "adaptability", "diversity", "coupling")

# Terms that reaching zero makes irreversible, per the verdict layer.
# f(C) is not among them: zero coupling is a configuration, not a
# structural loss, and the verdict layer does not treat it as one.
IRREVERSIBLE_TERMS = ("resonance_energy", "adaptability", "diversity")

DEFAULT_SAMPLES = 10000
DEFAULT_SEED = 0


@dataclass(frozen=True)
class Interval:
    """A closed range of possible values for one input.

    An interval says "the evidence puts this term somewhere in here" and
    nothing more. It carries no distribution: a wide interval is not a
    claim that the midpoint is most likely.
    """

    lo: float
    hi: float
    mode: Optional[float] = None   # most likely value, if one is known
    source: str = ""               # where the range came from

    def __post_init__(self) -> None:
        if self.hi < self.lo:
            raise ValueError(f"interval hi ({self.hi}) is below lo ({self.lo})")
        if self.mode is not None and not (self.lo <= self.mode <= self.hi):
            raise ValueError(f"mode {self.mode} is outside [{self.lo}, {self.hi}]")

    @property
    def width(self) -> float:
        return self.hi - self.lo

    @property
    def midpoint(self) -> float:
        return (self.lo + self.hi) / 2.0

    def contains(self, value: float) -> bool:
        return self.lo <= value <= self.hi

    @property
    def is_point(self) -> bool:
        """True when the interval expresses no uncertainty at all."""
        return self.width == 0.0

    def __str__(self) -> str:
        if self.is_point:
            return f"{self.lo:.4f}"
        return f"[{self.lo:.4f}, {self.hi:.4f}]"


def point(value: float, source: str = "") -> Interval:
    """An interval expressing a value known exactly (or asserted as such)."""
    return Interval(value, value, mode=value, source=source)


def from_relative(value: float, relative: float, source: str = "") -> Interval:
    """Interval from a point estimate and a relative uncertainty.

    A convenience for the common case of "roughly x, give or take 20%".
    The result is clamped at zero on the low side, since the gain terms
    are not meaningful below it.
    """
    if relative < 0:
        raise ValueError("relative uncertainty cannot be negative")
    delta = abs(value) * relative
    return Interval(max(0.0, value - delta), value + delta, mode=value, source=source)


def from_calibrations(calibrations: Sequence, term: str = "") -> Interval:
    """Interval spanning what several published derivations disagree about.

    When two cited adapters derive the same term from different data and
    return different numbers, that disagreement is real information about
    how well the term is known. Collapsing it to one number by picking a
    favourite hides the only honest uncertainty estimate available.

    Args:
        calibrations: Calibration objects (from `calibration.py`) for the
                      same M(S) term.
        term: Optional expected term name, checked if given.

    Returns:
        Interval spanning the values, sourced with every derivation used.
    """
    if not calibrations:
        raise ValueError("no calibrations supplied")
    terms = {c.term for c in calibrations}
    if len(terms) > 1:
        raise ValueError(f"calibrations span multiple terms: {sorted(terms)}")
    if term and terms != {term}:
        raise ValueError(f"expected term {term!r}, got {terms.pop()!r}")
    values = [c.value for c in calibrations]
    sources = "; ".join(sorted({c.source for c in calibrations}))
    return Interval(
        min(values), max(values),
        mode=None,
        source=f"disagreement across {len(values)} derivations: {sources}",
    )


def coupling_interval(metric, matrices: Sequence, source: str = "") -> Interval:
    """Range of f(C) over a set of candidate coupling matrices.

    f(C) is deliberately non-monotonic — it peaks at intermediate coupling
    — so its range cannot be read off the endpoints of a range of C the
    way the other terms can. The only safe method is to evaluate the
    candidates and take the extremes.

    Args:
        metric: A CoherenceMetric (its coupling_optimum defines the peak).
        matrices: Candidate coupling matrices spanning the plausible range.
        source: Where the candidate set came from.

    Returns:
        Interval over f(C).
    """
    if not len(matrices):
        raise ValueError("no candidate coupling matrices supplied")
    values = [metric.coupling_function(C) for C in matrices]
    return Interval(
        min(values), max(values),
        source=source or f"f(C) evaluated over {len(values)} candidate matrices",
    )


@dataclass
class UncertainState:
    """A system state whose inputs are ranges rather than point values.

    f(C) is supplied directly as an interval rather than as a coupling
    matrix, because the coupling function is not monotonic in C — use
    `coupling_interval` to build it from candidate matrices.
    """

    resonance_energy: Interval
    adaptability: Interval
    diversity: Interval
    coupling: Interval
    loss_rate: Interval
    energy_cost: Optional[Interval] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        for name in GAIN_TERMS:
            iv = getattr(self, name)
            if iv.lo < 0:
                raise ValueError(
                    f"{name} interval starts below zero ({iv.lo}); the tight "
                    "interval bounds depend on the gain terms being "
                    "non-negative, which is also what makes them monotone"
                )

    def intervals(self) -> Dict[str, Interval]:
        """All five input intervals, keyed by term name."""
        return {
            "resonance_energy": self.resonance_energy,
            "adaptability": self.adaptability,
            "diversity": self.diversity,
            "coupling": self.coupling,
            "loss_rate": self.loss_rate,
        }

    @property
    def is_certain(self) -> bool:
        """True when every input is a point value."""
        return all(iv.is_point for iv in self.intervals().values())


@dataclass
class UncertaintyReading:
    """What the inputs determine about M(S), and what they leave open."""

    m_interval: Interval                       # guaranteed bounds on M(S)
    verdict_determined: bool                   # one signal across the box?
    possible_signals: List[str] = field(default_factory=list)
    dominant_term: Optional[str] = None        # widest single contribution
    contributions: List[Tuple[str, float]] = field(default_factory=list)
    efficiency_interval: Optional[Interval] = None
    warnings: List[str] = field(default_factory=list)


def _m_of(r_e: float, a: float, d: float, f_c: float, l: float) -> float:
    """M(S) from scalar terms, with f(C) already evaluated."""
    return r_e * a * d * f_c - l


def _corner_signal(
    values: Dict[str, float],
    history: Optional[Sequence[float]],
) -> Tuple[float, str]:
    """M(S) and its signal at one corner of the input box."""
    m = _m_of(
        values["resonance_energy"], values["adaptability"], values["diversity"],
        values["coupling"], values["loss_rate"],
    )
    irreversible = [t for t in IRREVERSIBLE_TERMS if values[t] <= 0.0]
    full_history = list(history) if history else []
    full_history.append(m)
    traj = trajectory_from_history(full_history)
    ttc = time_to_collapse(full_history)
    return m, yield_signal(m, irreversible, ttc, traj)


def propagate(
    state: UncertainState,
    history: Optional[Sequence[float]] = None,
) -> UncertaintyReading:
    """Propagate input intervals through M(S) exactly.

    The gain term is a product of non-negative factors and the loss term
    is subtracted, so M(S) is monotone in every input. Its extremes are
    therefore at opposite corners of the input box, and the resulting
    bounds are tight — every value inside is attainable, and nothing
    outside is.

    Signals are evaluated at all corners of the box rather than only at
    the M(S) extremes, because the verdict layer does not depend on M(S)
    alone: BLACK is triggered by a structural term reaching zero, which
    can happen at a corner where M(S) is not extreme.

    Args:
        state: Inputs as intervals.
        history: Optional prior M(S) values, for the trajectory and
                 time-to-collapse bands. Without it only the
                 history-free bands (GREEN/RED/BLACK) can arise.

    Returns:
        UncertaintyReading with guaranteed bounds and the set of signals
        the evidence leaves open.
    """
    intervals = state.intervals()
    warnings: List[str] = []

    # Monotone: min at (lows, loss high), max at (highs, loss low).
    m_lo = _m_of(
        state.resonance_energy.lo, state.adaptability.lo, state.diversity.lo,
        state.coupling.lo, state.loss_rate.hi,
    )
    m_hi = _m_of(
        state.resonance_energy.hi, state.adaptability.hi, state.diversity.hi,
        state.coupling.hi, state.loss_rate.lo,
    )
    m_interval = Interval(m_lo, m_hi, source="monotone interval propagation")

    # Every corner of the five-dimensional box: 32 evaluations.
    signals = set()
    for combo in product(*[(iv.lo, iv.hi) for iv in intervals.values()]):
        values = dict(zip(intervals.keys(), combo))
        _, signal = _corner_signal(values, history)
        signals.add(signal)

    ordered = [s for s in ("GREEN", "AMBER", "RED", "BLACK") if s in signals]
    determined = len(ordered) == 1

    # One-at-a-time contribution: how much of the M(S) range each input
    # opens on its own, with the others held at their midpoints.
    mids = {name: iv.midpoint for name, iv in intervals.items()}
    contributions: List[Tuple[str, float]] = []
    for name, iv in intervals.items():
        if iv.is_point:
            contributions.append((name, 0.0))
            continue
        low_case = dict(mids, **{name: iv.lo})
        high_case = dict(mids, **{name: iv.hi})
        span = abs(
            _m_of(**{k: v for k, v in _as_args(high_case).items()})
            - _m_of(**{k: v for k, v in _as_args(low_case).items()})
        )
        contributions.append((name, span))
    contributions.sort(key=lambda kv: kv[1], reverse=True)
    dominant = contributions[0][0] if contributions and contributions[0][1] > 0 else None

    if state.is_certain:
        warnings.append(
            "every input was supplied as a point value, so this reading "
            "propagates no uncertainty — it restates the point estimate"
        )
    if not determined:
        warnings.append(
            "VERDICT UNDETERMINED: the inputs are consistent with "
            + " and ".join(ordered)
            + ". A single signal read off a point estimate would be an "
            "artifact of the point chosen, not a finding about the system."
        )
    if m_interval.contains(0.0) and not m_interval.is_point:
        warnings.append(
            "the M(S) interval spans zero — the evidence does not "
            "determine whether coherent gain exceeds loss"
        )
    if dominant is not None:
        warnings.append(
            f"'{dominant}' opens the widest range on its own "
            f"({contributions[0][1]:+.4f}); narrowing it would tighten the "
            "reading more than narrowing any other single input"
        )
        warnings.append(
            "contributions are one-at-a-time, with other inputs held at "
            "their midpoints. In a product, uncertainties interact, so "
            "these do not sum to the total width."
        )

    efficiency = None
    if state.energy_cost is not None:
        ec = state.energy_cost
        if ec.lo <= 0:
            warnings.append(
                "energy_cost interval reaches zero or below; the value ratio "
                "is undefined there and is not reported"
            )
        else:
            # M can be negative, so the ratio's extremes depend on its sign.
            candidates = [m / c for m in (m_lo, m_hi) for c in (ec.lo, ec.hi)]
            efficiency = Interval(min(candidates), max(candidates),
                                  source="M(S) interval over energy-cost interval")

    return UncertaintyReading(
        m_interval=m_interval,
        verdict_determined=determined,
        possible_signals=ordered,
        dominant_term=dominant,
        contributions=contributions,
        efficiency_interval=efficiency,
        warnings=warnings,
    )


def _as_args(values: Dict[str, float]) -> Dict[str, float]:
    """Map term names onto _m_of's parameter names."""
    return {
        "r_e": values["resonance_energy"],
        "a": values["adaptability"],
        "d": values["diversity"],
        "f_c": values["coupling"],
        "l": values["loss_rate"],
    }


@dataclass
class MonteCarloReading:
    """Distributional view of M(S) under sampled inputs."""

    median: float
    percentiles: Dict[int, float] = field(default_factory=dict)
    probability_negative: float = 0.0
    signal_probabilities: Dict[str, float] = field(default_factory=dict)
    samples: int = 0
    warnings: List[str] = field(default_factory=list)


def percentile(sorted_values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile of an already-sorted sequence."""
    if not sorted_values:
        raise ValueError("no values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def _sample(iv: Interval, rng: random.Random) -> float:
    """Draw one value from an interval.

    Uniform when only bounds are known — the maximum-entropy choice given
    no further information. Triangular when a mode was supplied, which is
    a stronger claim and should only be used when the mode is real.
    """
    if iv.is_point:
        return iv.lo
    if iv.mode is not None:
        return rng.triangular(iv.lo, iv.hi, iv.mode)
    return rng.uniform(iv.lo, iv.hi)


def monte_carlo(
    state: UncertainState,
    samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
    history: Optional[Sequence[float]] = None,
) -> MonteCarloReading:
    """Sample the input intervals to get a distribution over M(S).

    This answers the question intervals cannot: not "could M(S) be
    negative" but "how much of the probability mass is". That resolution
    is bought with two assumptions interval propagation does not make —
    a distribution shape per input, and independence between inputs —
    and both are reported in the output.

    Args:
        state: Inputs as intervals.
        samples: Number of draws.
        seed: Explicitly seeded so the reading is reproducible.
        history: Optional prior M(S) values for the trajectory bands.

    Returns:
        MonteCarloReading with percentiles and signal probabilities.
    """
    if samples < 1:
        raise ValueError("samples must be positive")

    rng = random.Random(seed)
    intervals = state.intervals()
    values: List[float] = []
    signal_counts: Dict[str, int] = {}

    for _ in range(samples):
        drawn = {name: _sample(iv, rng) for name, iv in intervals.items()}
        m, signal = _corner_signal(drawn, history)
        values.append(m)
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

    values.sort()
    negative = sum(1 for v in values if v < 0) / samples

    warnings = [
        "inputs were sampled INDEPENDENTLY. Real systems correlate — the "
        "stress that drains resonance energy usually erodes adaptability "
        "and diversity too — so the bad tail here is thinner than reality. "
        "The interval bounds from propagate() make no such assumption.",
    ]
    shapes = {
        "triangular" if iv.mode is not None else "uniform"
        for iv in intervals.values() if not iv.is_point
    }
    if shapes:
        warnings.append(
            f"distribution shape ({', '.join(sorted(shapes))}) is a modelling "
            "choice, not a measurement; uniform is the maximum-entropy "
            "default when only bounds are known"
        )

    return MonteCarloReading(
        median=percentile(values, 50),
        percentiles={p: percentile(values, p) for p in (5, 25, 50, 75, 95)},
        probability_negative=negative,
        signal_probabilities={k: v / samples for k, v in sorted(signal_counts.items())},
        samples=samples,
        warnings=warnings,
    )


def format_uncertainty(r: UncertaintyReading) -> str:
    """Human-readable rendering of an UncertaintyReading."""
    lines = [
        "=" * 70,
        f"M(S) ∈ {r.m_interval}    "
        f"VERDICT {'DETERMINED' if r.verdict_determined else 'UNDETERMINED'}",
        "=" * 70,
        f"  width           = {r.m_interval.width:.4f}",
        f"  possible signals= {', '.join(r.possible_signals)}",
    ]
    if r.efficiency_interval is not None:
        lines.append(f"  efficiency      ∈ {r.efficiency_interval} coherence/kWh")
    if r.contributions:
        lines.append("")
        lines.append("UNCERTAINTY CONTRIBUTION (one-at-a-time):")
        for name, span in r.contributions:
            lines.append(f"  {span:+.4f}  {name}")
    if r.warnings:
        lines.append("")
        lines.append("NOTES:")
        for w in r.warnings:
            lines.append(f"  - {w}")
    lines.extend([
        "",
        "An undetermined verdict is a fact about the evidence, not a "
        "licence to pick one.",
        "=" * 70,
    ])
    return "\n".join(lines)


# Demo
if __name__ == "__main__":
    print("A system whose point estimate reads GREEN, measured honestly:")
    print()

    uncertain = UncertainState(
        resonance_energy=Interval(0.60, 0.90, source="aerobic scope, seasonal range"),
        adaptability=Interval(0.50, 0.90, source="recovery rate, 4 observed events"),
        diversity=Interval(0.50, 0.90, source="response diversity, two survey years"),
        coupling=Interval(0.75, 0.95, source="f(C) over candidate coupling matrices"),
        loss_rate=Interval(0.15, 0.35, source="attrition, link rot, deferred maintenance"),
        energy_cost=Interval(40.0, 60.0),
        description="Community with honestly stated input ranges",
    )

    midpoints = {k: v.midpoint for k, v in uncertain.intervals().items()}
    point_estimate = _m_of(**_as_args(midpoints))
    _, point_signal = _corner_signal(midpoints, None)
    print(f"  point estimate at midpoints: M(S) = {point_estimate:+.4f}  -> {point_signal}")
    print("  Every input above is a range. Here is what they actually determine:")
    print()

    reading = propagate(uncertain)
    print(format_uncertainty(reading))
    print()

    mc = monte_carlo(uncertain, samples=20000)
    print("=" * 70)
    print("MONTE CARLO")
    print("=" * 70)
    for p, v in mc.percentiles.items():
        print(f"  p{p:<3d} = {v:+.4f}")
    print(f"  P(M(S) < 0) = {mc.probability_negative:.1%}")
    print("  signal probabilities:")
    for signal, prob in mc.signal_probabilities.items():
        print(f"    {signal:6s} {prob:.1%}")
    print()
    for w in mc.warnings:
        print(f"  - {w}")
    print("=" * 70)
