"""
Coherence Verdict Layer

Translate M(S) readings into machine-readable signals:
GREEN / AMBER / RED / BLACK.

Adapted from the verdict layer of the Metabolic Accounting framework
(https://github.com/JinnZ2/metabolic-accounting), preserving the same
four-band semantics: BLACK is reserved for irreversibility — a state
that no additional resonance energy can restore.

MEASUREMENT, NOT CONTROL
------------------------
This module REPORTS system state. It does not:
  - Recommend interventions
  - Optimize toward a target
  - Enforce conformity on any system

A verdict is a mirror, not a lever. Users decide what to do with
the reflection.

Every verdict is reproducible from inputs. No hidden state.
"""

from dataclasses import dataclass, field
from math import inf, isinf
from typing import List, Optional, Sequence

from ..core.coherence_metric import CoherenceMetric, SystemState


# --- Irreversibility thresholds -----------------------------------------
# A system that has lost *all* viable strategies (diversity == 0), *all*
# capacity to recover (adaptability == 0), or *all* constructive flow
# (resonance_energy == 0) is in a configuration no amount of input can
# undo from within. Crossing any of these is BLACK.
DIVERSITY_IRREVERSIBLE = 0.0
ADAPTABILITY_IRREVERSIBLE = 0.0
RESONANCE_IRREVERSIBLE = 0.0


@dataclass
class CoherenceVerdict:
    """Machine-readable judgment of system coherence."""

    signal: str                          # GREEN | AMBER | RED | BLACK
    trajectory: str                      # IMPROVING | STABLE | DEGRADING
    coherence: float                     # M(S)
    efficiency: Optional[float]          # M(S) / energy_cost (if known)
    time_to_collapse: Optional[float]    # periods until M(S) crosses zero
    irreversible_components: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _irreversible_components(state: SystemState) -> List[str]:
    """Return names of state components that have collapsed to zero."""
    flagged: List[str] = []
    if state.diversity <= DIVERSITY_IRREVERSIBLE:
        flagged.append("diversity")
    if state.adaptability <= ADAPTABILITY_IRREVERSIBLE:
        flagged.append("adaptability")
    if state.resonance_energy <= RESONANCE_IRREVERSIBLE:
        flagged.append("resonance_energy")
    return flagged


def trajectory_from_history(history: Sequence[float]) -> str:
    """Classify an M(S) time series as IMPROVING, STABLE, or DEGRADING.

    Uses the sign of the mean first-difference over the window. A history
    of fewer than two points is STABLE by default (no motion observed).
    """
    if len(history) < 2:
        return "STABLE"
    deltas = [b - a for a, b in zip(history[:-1], history[1:])]
    mean_delta = sum(deltas) / len(deltas)
    # tolerance relative to the span so flat drifts don't read as motion
    span = max(history) - min(history)
    tol = max(1e-9, 0.01 * span)
    if mean_delta > tol:
        return "IMPROVING"
    if mean_delta < -tol:
        return "DEGRADING"
    return "STABLE"


def time_to_collapse(history: Sequence[float]) -> Optional[float]:
    """Estimate periods until M(S) crosses zero, extrapolating linearly.

    Returns None if:
      - history has fewer than two points,
      - the current value is already non-positive,
      - the trajectory is flat or improving (no collapse projected).
    """
    if len(history) < 2:
        return None
    current = history[-1]
    if current <= 0:
        return 0.0
    deltas = [b - a for a, b in zip(history[:-1], history[1:])]
    mean_delta = sum(deltas) / len(deltas)
    if mean_delta >= 0:
        return None
    # mean_delta < 0 and current > 0
    return current / (-mean_delta)


def yield_signal(
    coherence: float,
    irreversible: Sequence[str],
    ttc: Optional[float],
    trajectory: str,
) -> str:
    """GREEN / AMBER / RED / BLACK for the coherence state.

    BLACK  if any structural component is irreversibly collapsed.
    RED    if M(S) < 0, or time_to_collapse <= 1 period.
    AMBER  if M(S) small-positive while degrading, or ttc <= 5 periods.
    GREEN  otherwise.
    """
    if irreversible:
        return "BLACK"
    if coherence < 0:
        return "RED"
    if ttc is not None and ttc <= 1.0:
        return "RED"
    if ttc is not None and ttc <= 5.0:
        return "AMBER"
    if trajectory == "DEGRADING" and coherence < 0.5:
        return "AMBER"
    return "GREEN"


def assess(
    state: SystemState,
    history: Optional[Sequence[float]] = None,
    metric: Optional[CoherenceMetric] = None,
) -> CoherenceVerdict:
    """Produce a verdict for a single system state.

    Args:
        state: Current SystemState.
        history: Optional sequence of prior M(S) values (oldest first).
                 When supplied, trajectory and time_to_collapse are
                 computed from it. The current M(S) is appended
                 automatically for the projection.
        metric: Optional CoherenceMetric instance (defaults to new one).

    Returns:
        CoherenceVerdict — signal, trajectory, warnings, and raw numbers.
    """
    metric = metric or CoherenceMetric()
    m_s = metric.calculate_from_state(state)
    efficiency = metric.efficiency_ratio(state)

    full_history: List[float] = list(history) if history else []
    full_history.append(m_s)

    traj = trajectory_from_history(full_history)
    ttc = time_to_collapse(full_history)
    irreversible = _irreversible_components(state)
    signal = yield_signal(m_s, irreversible, ttc, traj)

    warnings: List[str] = []

    if irreversible:
        warnings.append(
            "IRREVERSIBLE: "
            + ", ".join(irreversible)
            + " — component(s) at zero; no input restores these from within."
        )

    if m_s < 0:
        warnings.append(
            f"M(S) = {m_s:.3f} is negative — loss rate exceeds coherent gain."
        )

    if ttc is not None and not isinf(ttc) and ttc <= 5.0:
        warnings.append(
            f"projected collapse in ~{ttc:.2f} periods at current trajectory"
        )

    if traj == "DEGRADING" and not irreversible and m_s >= 0:
        warnings.append(
            "trajectory is degrading — coherence eroding despite positive M(S)"
        )

    if state.loss_rate > 0 and state.adaptability > 0:
        # ratio of entropy drag to recovery capacity; >1 means drag dominates
        drag_ratio = state.loss_rate / state.adaptability
        if drag_ratio > 1.0:
            warnings.append(
                f"loss_rate / adaptability = {drag_ratio:.2f} > 1 — "
                "entropy outpaces recovery capacity"
            )

    return CoherenceVerdict(
        signal=signal,
        trajectory=traj,
        coherence=m_s,
        efficiency=efficiency,
        time_to_collapse=ttc,
        irreversible_components=irreversible,
        warnings=warnings,
    )


def format_verdict(v: CoherenceVerdict) -> str:
    """Human-readable rendering of a CoherenceVerdict."""
    lines = [
        "=" * 70,
        f"SIGNAL: {v.signal}    TRAJECTORY: {v.trajectory}",
        "=" * 70,
        f"  M(S)        = {v.coherence:+.4f}",
    ]
    if v.efficiency is not None:
        lines.append(f"  efficiency  = {v.efficiency:+.4f} coherence/kWh")
    if v.time_to_collapse is not None:
        lines.append(f"  ttc         = {v.time_to_collapse:.2f} periods")
    else:
        lines.append("  ttc         = n/a (no collapse projected)")
    if v.warnings:
        lines.append("")
        lines.append("WARNINGS:")
        for w in v.warnings:
            lines.append(f"  - {w}")
    lines.extend([
        "",
        "This is a reading, not a prescription. Decide what it means for you.",
        "=" * 70,
    ])
    return "\n".join(lines)


# Demo
if __name__ == "__main__":
    import numpy as np
    from ..core.coherence_metric import SystemState, PHI

    healthy = SystemState(
        resonance_energy=0.9,
        adaptability=0.85,
        diversity=0.8,
        coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
        loss_rate=0.1,
        energy_cost=6,
        description="Healthy coherent system",
    )

    eroding_history = [0.40, 0.32, 0.24, 0.17]
    eroding_now = SystemState(
        resonance_energy=0.5,
        adaptability=0.3,
        diversity=0.4,
        coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
        loss_rate=0.45,
        energy_cost=40,
        description="Slowly collapsing system",
    )

    collapsed = SystemState(
        resonance_energy=0.2,
        adaptability=0.1,
        diversity=0.0,   # irreversible: all strategies extinct
        coupling_matrix=np.array([[2.0, 0.0], [0.0, 2.0]]),
        loss_rate=0.9,
        energy_cost=500,
        description="Monoculture with no viable alternatives",
    )

    for state, hist in [(healthy, None), (eroding_now, eroding_history), (collapsed, None)]:
        print(format_verdict(assess(state, history=hist)))
        print()
