"""
Dormancy: folding to a seed, and the physics of waiting

M(S) is a *flux* measure. It reports the rate at which a system converts
constructive interaction into coherence. That makes it blind to one
distinction biology treats as fundamental:

    a dormant system and a dead system both read R_e = A = D = 0.

The verdict layer calls that BLACK — irreversible, no input restores it
from within. For a genuinely collapsed system that is right. For a seed,
a spore, or a tardigrade in tun state it is a false positive with real
consequences: anhydrobiotic tardigrades lose >95% of body water and
suspend metabolism, and *resume*. Judean date palm seeds germinated
after ~2000 years. Nothing in a flux reading separates those cases from
death, because during dormancy there is no flux to read.

**This module does not make M(S) able to tell them apart. Nothing can,
from flux alone.** It supplies the second, structural measurement
channel that the distinction actually requires, and is explicit that a
BLACK reading plus an intact seed means "dormant", while a BLACK reading
with no seed evidence means exactly what it says.

WHAT A SEED IS
--------------
Following the seed-physics formulation (JinnZ2/Seed-physics): *"The seed
doesn't describe the structure. It IS the structure at minimum energy."*
What survives folding is not the system's magnitude but its
*proportions* — six amplitudes on octahedral vertices with the
conservation law Sum(S_i) = E holding exactly at every shell. Proportions
are scale-free, which is precisely the property something must have to
re-expand at a scale the future decides.

The mandala-bloom operation (JinnZ2/Mandala-Computing) runs the other
way: a parent atlas entry blooms into a child manifold with its own
metric. Folding is its inverse — a manifold contracts to a point — and
the thing that makes the inverse *faithful* is carrying the instrument
tensor back with it. A seed that keeps amplitudes but loses the metric
re-expands into the wrong shape. So a seed here stores three things:
the proportions, the conserved total, and enough of the measurement
context to read the proportions back correctly.

THE PHYSICS OF WAITING IS NOT FREE
----------------------------------
Three quantitative facts keep this from being wishful:

1. **Folding costs energy.** Sporulation and anhydrobiosis are
   expensive: trehalose synthesis, LEA protein expression, controlled
   water loss. A system that waits too long cannot afford to fold at
   all. The option closes before the system dies, and `fold_window`
   reports that closing. This is a measurement of a disappearing
   option, not advice about when to use it.

2. **Preservation decays on a clock.** Orthodox seed longevity follows
   the Ellis & Roberts viability equation (1980, Annals of Botany 45:13):
   viability in probits falls linearly with storage time, v = K_i - p/sigma,
   where the time constant obeys

       log(sigma) = K_E - C_W*log(m) - C_H*t - C_Q*t^2

   with m the moisture content and t the temperature. Dormancy buys
   duration by giving up rate; the exchange rate is this equation, and
   it is finite.

3. **Over-compression destroys the seed.** The negative
   longevity-moisture relation has a floor at roughly 2-6% moisture;
   drying below it buys nothing and eventually damages what is being
   preserved. There is a minimum viable seed, and compressing past it
   is not better compression, it is loss.

WHERE THE THREE FAILURE MODES SHOW UP
-------------------------------------
The conditions that make folding relevant are already measured
elsewhere in this package, and each is a different kind of trouble:

    degradation      `early_warning.critical_slowing_down` — recovery
                     rate eroding, with the fold window narrowing
                     as R_e falls.
    cannot network   `coupling_physics.spectrum` — a partitioned network
                     has lambda_2 = 0, so no coupling strength
                     synchronizes it. This is the case where folding per
                     surviving component and waiting for reconnection is
                     a different outcome from failing.
    unexpected       `uncertainty.propagate` — a verdict that is not
                     determined by the evidence. Folding while the
                     reading is ambiguous preserves the option that the
                     bad branch turns out to be the real one.

None of these is read here as a signal to fold. They are where you would
look to know whether the question is live.

MEASUREMENT, NOT CONTROL
------------------------
This module reports whether folding is still possible, what a fold would
preserve, what it would destroy, and how long the result stays viable.
It does not decide to fold, trigger a fold, or recommend one. A
community that would rather end than wait is making a legitimate choice,
and dormancy is not a value the framework gets to impose.

Standard library only.
"""

from dataclasses import dataclass, field
from math import erf, inf, isinf, log10, sqrt
from typing import Any, Dict, List, Optional, Sequence

# Terms whose proportions a seed preserves. f(C) is included because the
# coupling *shape* is part of what must be re-expanded; L is not, because
# the loss rate is a property of the environment the system was in, not
# of the structure it is preserving.
SEED_TERMS = ("resonance_energy", "adaptability", "diversity", "coupling")

# Ellis & Roberts viability constants. These are measured for orthodox
# *seeds*; K_E is the extrapolated log-sigma at 1% moisture and 0 C, and
# C_W varies from about 4.5 (rape) to 6.3 (mung bean) across species.
# Supplied as documented defaults so the equation is runnable, NOT as a
# claim that any given system shares them.
DEFAULT_K_E = 8.0
DEFAULT_C_W = 5.4      # mid-range of the reported 4.5-6.3 span
DEFAULT_C_H = 0.05
DEFAULT_C_Q = 0.000478

# The low-moisture limit: below roughly this residual activity, further
# compression stops extending longevity and starts destroying structure.
MIN_VIABLE_RESIDUAL = 0.02
MAX_USEFUL_RESIDUAL = 0.06

# Fraction of remaining resonance energy a fold consumes. Folding is an
# active, costly reconfiguration, not a passive shutting-down.
DEFAULT_FOLD_COST = 0.15


def _phi(x: float) -> float:
    """Standard normal CDF, for converting probit viability to a fraction."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _probit(p: float) -> float:
    """Approximate inverse normal CDF (Acklam's rational approximation).

    Used only to convert an initial viability fraction into the probit
    scale the Ellis & Roberts equation is written in.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("probit requires a probability strictly between 0 and 1")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = sqrt(-2 * log10(p) * 2.302585092994046)
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > p_high:
        q = sqrt(-2 * log10(1 - p) * 2.302585092994046)
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


@dataclass(frozen=True)
class SeedState:
    """A system folded to its scale-free invariant.

    Carries proportions rather than magnitudes, on the seed-physics
    principle that the seed *is* the structure at minimum energy. The
    conserved total plays the role of E in Sum(S_i) = E: it records how
    much there was, so a re-expansion can report honestly how much of
    the original scale it recovered.
    """

    proportions: Dict[str, float]          # sums to 1 across SEED_TERMS
    conserved_total: float                 # the E the proportions were taken from
    metric_signature: Dict[str, Any] = field(default_factory=dict)
    residual_activity: float = 0.05        # the "moisture content" analogue
    folded_at: float = 0.0                 # period index at folding
    provenance: List[str] = field(default_factory=list)
    lost: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        total = sum(self.proportions.values())
        if self.proportions and abs(total - 1.0) > 1e-9:
            raise ValueError(f"seed proportions must sum to 1, got {total}")
        if self.conserved_total < 0:
            raise ValueError("conserved total cannot be negative")

    @property
    def is_degenerate(self) -> bool:
        """True when a term's proportion is zero — that term cannot re-expand.

        A seed preserves ratios. A ratio of zero is preserved perfectly
        and re-expands to zero, so a structural term lost before folding
        is not recoverable by unfolding.
        """
        return any(v <= 0.0 for v in self.proportions.values())


@dataclass
class FoldWindow:
    """Whether folding is still affordable, and what it would cost."""

    open: bool
    fold_cost: float                    # energy the fold itself consumes
    available: float                    # energy on hand
    margin: float                       # available - cost
    warnings: List[str] = field(default_factory=list)


@dataclass
class ViabilityReading:
    """How much of a folded seed is still able to re-expand."""

    viable_fraction: float
    sigma: float                        # Ellis & Roberts time constant
    periods_elapsed: float
    half_life: Optional[float] = None
    flag: str = ""                      # VIABLE | DEGRADING | NONVIABLE
    source: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class DormancyReading:
    """The structural channel M(S) cannot supply on its own."""

    state: str                          # DORMANT | REVIVABLE | SEED_LOST
    #                                     | NEVER_FOLDED
    viability: Optional[ViabilityReading] = None
    seed: Optional[SeedState] = None
    warnings: List[str] = field(default_factory=list)


def fold_window(
    resonance_energy: float,
    fold_cost_fraction: float = DEFAULT_FOLD_COST,
) -> FoldWindow:
    """Report whether a system can still afford to fold.

    Folding is an active reconfiguration — trehalose synthesis, protein
    expression, controlled water loss — and it is paid for out of the
    energy the system still has. A system that degrades past the cost of
    folding loses the option to fold before it loses everything else.

    This reports the closing of that option. It does not advise using it:
    a system that would rather end than wait is making a real choice.

    Args:
        resonance_energy: R_e, the constructive energy currently available.
        fold_cost_fraction: Share of a healthy system's energy that
                            completing a fold consumes.

    Returns:
        FoldWindow. `open` is False once the cost exceeds what is left.
    """
    if not 0.0 <= fold_cost_fraction <= 1.0:
        raise ValueError("fold cost fraction must be in [0, 1]")
    cost = fold_cost_fraction
    available = max(0.0, resonance_energy)
    margin = available - cost
    warnings: List[str] = []

    if margin < 0:
        warnings.append(
            f"fold window CLOSED: folding costs {cost:.3f} and only "
            f"{available:.3f} remains. Compression to a seed is no longer "
            "reachable from here — the option expired before the system did."
        )
    elif margin < cost:
        warnings.append(
            f"fold window NARROW: margin {margin:.3f} is under the fold cost "
            f"{cost:.3f} itself. A further decline of that size closes it."
        )
    return FoldWindow(open=margin >= 0, fold_cost=cost, available=available,
                      margin=margin, warnings=warnings)


def fold(
    resonance_energy: float,
    adaptability: float,
    diversity: float,
    coupling: float,
    residual_activity: float = 0.05,
    folded_at: float = 0.0,
    metric_signature: Optional[Dict[str, Any]] = None,
    fold_cost_fraction: float = DEFAULT_FOLD_COST,
) -> SeedState:
    """Compress a system's structural terms to a scale-free seed.

    What survives is the *ratio* between the structural terms and the
    total they were drawn from. Magnitude does not survive, and neither
    does anything the seed is not told to carry — this function names
    both in the returned seed's `lost` list rather than leaving the
    caller to assume a lossless round trip.

    Args:
        resonance_energy: R_e at folding.
        adaptability: A at folding.
        diversity: D at folding.
        coupling: f(C) at folding.
        residual_activity: The "moisture content" analogue — how much
                           activity the dormant state retains. Lower
                           preserves longer, down to the viable floor.
        folded_at: Period index, so elapsed time can be computed later.
        metric_signature: What is needed to read the proportions back
                          correctly on re-expansion — the mandala
                          instrument tensor's role. Carried verbatim.
        fold_cost_fraction: Passed to the window check.

    Returns:
        SeedState.

    Raises:
        ValueError: if the fold window is closed, or every structural
                    term is zero (there is nothing left to preserve).
    """
    terms = {
        "resonance_energy": max(0.0, resonance_energy),
        "adaptability": max(0.0, adaptability),
        "diversity": max(0.0, diversity),
        "coupling": max(0.0, coupling),
    }
    total = sum(terms.values())
    if total <= 0:
        raise ValueError(
            "every structural term is zero: there is no structure left to "
            "compress. This is the case where BLACK means what it says."
        )

    window = fold_window(resonance_energy, fold_cost_fraction)
    if not window.open:
        raise ValueError(
            f"fold window is closed (R_e = {resonance_energy:.3f} < cost "
            f"{window.fold_cost:.3f}); the system cannot afford to fold"
        )

    lost = [
        "absolute magnitude — only ratios survive; re-expansion happens at "
        "whatever scale the environment later permits, not this one",
        "loss rate L — a property of the environment the system was in, "
        "not of the structure being preserved",
        "history — trajectory, time-to-collapse and early-warning state "
        "are all flux measurements with no flux to measure",
    ]
    provenance = [
        "seed-physics: proportions are the structure at minimum energy "
        "(JinnZ2/Seed-physics)",
        "mandala fold: the inverse of bloom carries the metric back with "
        "the amplitudes (JinnZ2/Mandala-Computing)",
    ]
    warnings_terms = [k for k, v in terms.items() if v <= 0.0]
    if warnings_terms:
        lost.append(
            "structural terms already at zero before folding ("
            + ", ".join(sorted(warnings_terms))
            + ") — a preserved ratio of zero re-expands to zero"
        )

    if residual_activity < MIN_VIABLE_RESIDUAL:
        provenance.append(
            f"residual activity {residual_activity:.3f} is below the "
            f"{MIN_VIABLE_RESIDUAL:.0%} floor: further compression stops "
            "extending longevity and starts destroying what is preserved"
        )

    return SeedState(
        proportions={k: v / total for k, v in terms.items()},
        conserved_total=total,
        metric_signature=dict(metric_signature or {}),
        residual_activity=residual_activity,
        folded_at=folded_at,
        provenance=provenance,
        lost=lost,
    )


def viability(
    seed: SeedState,
    periods_elapsed: float,
    stress: float = 0.0,
    initial_viability: float = 0.98,
    k_e: float = DEFAULT_K_E,
    c_w: float = DEFAULT_C_W,
    c_h: float = DEFAULT_C_H,
    c_q: float = DEFAULT_C_Q,
) -> ViabilityReading:
    """Fraction of a seed still able to re-expand, after waiting.

    Implements the Ellis & Roberts viability equation (1980, Annals of
    Botany 45:13). Viability in probits declines linearly with storage
    time, v = K_i - p/sigma, and the time constant sigma depends on
    residual activity (the moisture term) and stress (the temperature
    term):

        log10(sigma) = K_E - C_W*log10(m) - C_H*t - C_Q*t^2

    Lower residual activity and lower stress both buy duration, which is
    the whole trade dormancy makes.

    CAVEAT, LOUDLY: the default constants are measured for orthodox
    seeds. Applying them to a non-seed system is an analogy, not a
    measurement, and the returned reading says so. Supply constants
    fitted to the system in question if you have them.

    Args:
        seed: The folded state.
        periods_elapsed: Time waited since folding.
        stress: Environmental stress during dormancy (temperature term).
        initial_viability: Fraction viable at the moment of folding.
        k_e, c_w, c_h, c_q: Viability constants.

    Returns:
        ViabilityReading with the surviving fraction and a flag.
    """
    if periods_elapsed < 0:
        raise ValueError("elapsed periods cannot be negative")

    warnings = [
        "viability constants are measured for orthodox seeds; using them "
        "for another kind of system is an analogy, not a measurement",
    ]

    # Drying below the floor buys no further longevity, and the seed
    # itself starts to degrade — so the effective moisture term is
    # clamped, and over-compression is charged as lost initial viability.
    m = seed.residual_activity
    effective_m = max(MIN_VIABLE_RESIDUAL, m)
    k_i = _probit(min(0.999999, max(1e-6, initial_viability)))

    if m < MIN_VIABLE_RESIDUAL:
        penalty = (MIN_VIABLE_RESIDUAL - m) / MIN_VIABLE_RESIDUAL
        k_i *= max(0.0, 1.0 - penalty)
        warnings.append(
            f"residual activity {m:.3f} is below the {MIN_VIABLE_RESIDUAL:.0%} "
            "floor — over-compression, charged against initial viability "
            "rather than rewarded with longevity"
        )
    elif m > MAX_USEFUL_RESIDUAL:
        warnings.append(
            f"residual activity {m:.3f} is above the "
            f"{MAX_USEFUL_RESIDUAL:.0%} point where the negative "
            "longevity-moisture relation is well established; the seed is "
            "storing wetter, and shorter, than it needs to"
        )

    log_sigma = (k_e
                 - c_w * log10(effective_m * 100.0)   # moisture as a percentage
                 - c_h * stress
                 - c_q * stress * stress)
    sigma = 10.0 ** log_sigma

    if seed.is_degenerate:
        warnings.append(
            "seed has a zero proportion: that structural term re-expands to "
            "zero however viable the rest of the seed remains"
        )

    v_probit = k_i - (periods_elapsed / sigma if sigma > 0 else inf)
    fraction = _phi(v_probit)
    half_life = sigma * k_i if k_i > 0 else None

    if fraction >= 0.5:
        flag = "VIABLE"
    elif fraction > 0.01:
        flag = "DEGRADING"
        warnings.append(
            f"under half the seed remains viable after {periods_elapsed:g} "
            "periods; the wait is consuming what it was meant to preserve"
        )
    else:
        flag = "NONVIABLE"
        warnings.append(
            "viability is effectively exhausted — the seed waited longer "
            "than it could. This is the branch where BLACK becomes correct."
        )

    return ViabilityReading(
        viable_fraction=fraction,
        sigma=sigma,
        periods_elapsed=periods_elapsed,
        half_life=half_life,
        flag=flag,
        source="Ellis & Roberts 1980, Annals of Botany 45:13 (viability equation)",
        warnings=warnings,
    )


def unfold(
    seed: SeedState,
    available_energy: float,
    viability_reading: Optional[ViabilityReading] = None,
) -> Dict[str, float]:
    """Re-expand a seed at whatever scale the environment now permits.

    Proportions are restored exactly; magnitude is set by what is
    available now, not by what was available at folding. Where a
    viability reading is supplied, the surviving fraction scales the
    result — a partly-degraded seed re-expands to a smaller system, not
    to a proportionally wrong one.

    Args:
        seed: The folded state.
        available_energy: Total structural budget the environment allows.
        viability_reading: Optional decay reading; full viability assumed
                           if omitted.

    Returns:
        Dict of re-expanded structural terms.

    Raises:
        ValueError: if the seed is nonviable, or no energy is available.
    """
    if available_energy <= 0:
        raise ValueError("re-expansion needs a positive energy budget")
    fraction = 1.0 if viability_reading is None else viability_reading.viable_fraction
    if viability_reading is not None and viability_reading.flag == "NONVIABLE":
        raise ValueError(
            "seed is nonviable; there is nothing left to re-expand. The "
            "structure did not survive the wait."
        )
    scale = available_energy * fraction
    return {term: proportion * scale for term, proportion in seed.proportions.items()}


def assess_dormancy(
    seed: Optional[SeedState],
    periods_elapsed: float = 0.0,
    stress: float = 0.0,
) -> DormancyReading:
    """The structural reading that sits alongside a BLACK M(S) verdict.

    A BLACK signal says the flux measurement found nothing. This says
    whether there is preserved structure behind that silence.

    Args:
        seed: The folded state, or None if the system never folded.
        periods_elapsed: Time waited since folding.
        stress: Environmental stress during the wait.

    Returns:
        DormancyReading.
    """
    if seed is None:
        return DormancyReading(
            state="NEVER_FOLDED",
            warnings=[
                "no seed evidence. A BLACK M(S) reading stands unqualified: "
                "there is no structural channel suggesting anything is "
                "waiting. Absence of a seed is not proof of death, but it "
                "is not evidence of dormancy either.",
            ],
        )

    reading = viability(seed, periods_elapsed, stress=stress)
    warnings = list(reading.warnings)

    if reading.flag == "NONVIABLE":
        state = "SEED_LOST"
        warnings.append(
            "the seed existed and did not survive the wait. BLACK is now "
            "the correct reading, arrived at honestly rather than by "
            "mistaking dormancy for death."
        )
    elif reading.flag == "DEGRADING":
        state = "REVIVABLE"
        warnings.append(
            f"{reading.viable_fraction:.1%} of the seed remains able to "
            "re-expand, and re-expansion would be to a smaller system than "
            "the one that folded"
        )
    else:
        state = "DORMANT"
        warnings.append(
            "M(S) reads zero because there is no flux, not because there is "
            "no structure. This is the false positive BLACK cannot avoid on "
            "its own."
        )

    return DormancyReading(state=state, viability=reading, seed=seed,
                           warnings=warnings)


def format_dormancy(r: DormancyReading) -> str:
    """Human-readable rendering of a DormancyReading."""
    lines = [
        "=" * 70,
        f"DORMANCY: {r.state}",
        "=" * 70,
    ]
    if r.seed is not None:
        lines.append("  preserved proportions:")
        for term, value in sorted(r.seed.proportions.items()):
            lines.append(f"    {value:.4f}  {term}")
        lines.append(f"  conserved total    = {r.seed.conserved_total:.4f}")
        lines.append(f"  residual activity  = {r.seed.residual_activity:.4f}")
    if r.viability is not None:
        v = r.viability
        lines.append(f"  viable fraction    = {v.viable_fraction:.4f}")
        lines.append(f"  sigma (time const) = {v.sigma:.2f} periods")
        if v.half_life is not None and not isinf(v.half_life):
            lines.append(f"  half-life          = {v.half_life:.2f} periods")
        lines.append(f"  elapsed            = {v.periods_elapsed:g} periods")
    if r.seed is not None and r.seed.lost:
        lines.append("")
        lines.append("NOT PRESERVED BY FOLDING:")
        for item in r.seed.lost:
            lines.append(f"  - {item}")
    if r.warnings:
        lines.append("")
        lines.append("NOTES:")
        for w in r.warnings:
            lines.append(f"  - {w}")
    lines.extend([
        "",
        "Whether waiting is worth it is not a measurement. That part is yours.",
        "=" * 70,
    ])
    return "\n".join(lines)


# Demo
if __name__ == "__main__":
    print("A system degrading toward the point where folding stops being possible:")
    print()
    for r_e in (0.80, 0.40, 0.20, 0.16, 0.10):
        w = fold_window(r_e)
        status = "open" if w.open else "CLOSED"
        print(f"  R_e = {r_e:.2f} -> fold window {status:6s} "
              f"(margin {w.margin:+.3f})")
    print()

    seed = fold(
        resonance_energy=0.40,
        adaptability=0.30,
        diversity=0.55,
        coupling=0.70,
        residual_activity=0.04,
        folded_at=12.0,
        metric_signature={"coupling_optimum": "phi", "calibration": "response_diversity"},
    )

    # The trade dormancy makes: duration bought with stillness. Cold dry
    # storage lasts orders of magnitude longer than warm storage, and the
    # Ellis & Roberts constants say by how much.
    print("Viability against elapsed time, at three stress levels:")
    print()
    print(f"  {'periods':>10s}  " + "  ".join(f"stress {s:<5g}" for s in (0, 20, 40)))
    for elapsed in (0, 100, 1000, 10000, 100000):
        cells = []
        for stress in (0, 20, 40):
            v = viability(seed, float(elapsed), stress=stress)
            cells.append(f"{v.viable_fraction:6.1%} {v.flag[:4]:<5s}")
        print(f"  {elapsed:10d}  " + " ".join(cells))
    print()
    print("  sigma: " + ", ".join(
        f"stress {s} -> {viability(seed, 0.0, stress=s).sigma:,.0f} periods"
        for s in (0, 20, 40)))
    print()

    # A seed that waited too long, under stress.
    print(format_dormancy(assess_dormancy(seed, periods_elapsed=8000.0, stress=40.0)))
    print()

    # The contrast that matters: no seed at all.
    print(format_dormancy(assess_dormancy(None)))
    print()

    print("Re-expansion at a smaller scale than the system that folded:")
    print(f"  folded from a system totalling {seed.conserved_total:.4f}")
    revived = unfold(seed, available_energy=1.2,
                     viability_reading=viability(seed, 1000.0, stress=20.0))
    for term, value in sorted(revived.items()):
        print(f"    {term:20s} {value:.4f}")
    print(f"  re-expanded total {sum(revived.values()):.4f}")
    print()
    print("Proportions survive; magnitude is whatever the world now allows.")
