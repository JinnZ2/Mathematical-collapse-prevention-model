"""
Sensitivity Analysis for M(S)

Finite-difference perturbation of each coherence input to reveal which
lever actually moves the reading.

This module REVEALS structure; it does not recommend action. Knowing
that, at a given operating point, diversity moves M(S) twice as much
as resonance_energy does not mean "push diversity up." It means: if
you want to understand your reading, pay attention to diversity.

Transparency tool, not an optimizer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..core.coherence_metric import CoherenceMetric, SystemState


PARAMETERS = (
    "resonance_energy",
    "adaptability",
    "diversity",
    "coupling_matrix",
    "loss_rate",
)


@dataclass
class SensitivityReading:
    """Per-parameter local sensitivity of M(S)."""

    baseline_m: float
    deltas: Dict[str, float] = field(default_factory=dict)           # ΔM for +epsilon
    normalized: Dict[str, float] = field(default_factory=dict)       # ΔM / epsilon (slope)
    ranking: List[Tuple[str, float]] = field(default_factory=list)   # sorted by |slope|


def _perturbed_state(state: SystemState, name: str, delta: float) -> SystemState:
    """Return a copy of state with one parameter perturbed by delta.

    For scalar parameters: value += delta.
    For coupling_matrix:   C  += delta * I (scaled identity) to keep the
                           perturbation isotropic and scalar-summarisable.
    """
    kwargs = dict(
        resonance_energy=state.resonance_energy,
        adaptability=state.adaptability,
        diversity=state.diversity,
        coupling_matrix=np.array(state.coupling_matrix, copy=True),
        loss_rate=state.loss_rate,
        energy_cost=state.energy_cost,
        population=state.population,
        description=state.description,
    )
    if name == "coupling_matrix":
        n = kwargs["coupling_matrix"].shape[0]
        kwargs["coupling_matrix"] = kwargs["coupling_matrix"] + delta * np.eye(n)
    else:
        kwargs[name] = kwargs[name] + delta
    return SystemState(**kwargs)


def sensitivity(
    state: SystemState,
    epsilon: float = 0.01,
    metric: Optional[CoherenceMetric] = None,
) -> SensitivityReading:
    """Measure how M(S) responds to a small perturbation of each input.

    Uses a central difference: slope ≈ (M(x + ε) - M(x - ε)) / (2ε).
    More accurate than forward difference and symmetric around the
    operating point, which matters for the coupling function since
    f(C) peaks at an intermediate value.

    Args:
        state:   Operating point to probe.
        epsilon: Perturbation size. Default 0.01 — small enough for local
                 linearization at most operating points.
        metric:  Optional CoherenceMetric (defaults to a fresh one).

    Returns:
        SensitivityReading with:
          - baseline_m: M(S) at the operating point
          - deltas:     signed ΔM for a +epsilon bump in each parameter
          - normalized: slope (ΔM / epsilon) — comparable across params
          - ranking:    parameters sorted by |slope|, most influential first
    """
    metric = metric or CoherenceMetric()
    baseline = metric.calculate_from_state(state)

    deltas: Dict[str, float] = {}
    normalized: Dict[str, float] = {}
    for name in PARAMETERS:
        m_plus = metric.calculate_from_state(_perturbed_state(state, name, epsilon))
        m_minus = metric.calculate_from_state(_perturbed_state(state, name, -epsilon))
        slope = (m_plus - m_minus) / (2.0 * epsilon)
        deltas[name] = m_plus - baseline
        normalized[name] = slope

    ranking = sorted(normalized.items(), key=lambda kv: abs(kv[1]), reverse=True)

    return SensitivityReading(
        baseline_m=baseline,
        deltas=deltas,
        normalized=normalized,
        ranking=ranking,
    )


def format_sensitivity(reading: SensitivityReading) -> str:
    """Human-readable rendering of a SensitivityReading."""
    lines = [
        "=" * 70,
        f"SENSITIVITY AT M(S) = {reading.baseline_m:+.4f}",
        "=" * 70,
        "Slopes (∂M/∂x) at the operating point, ranked by magnitude:",
        "",
    ]
    for name, slope in reading.ranking:
        direction = "↑" if slope > 0 else ("↓" if slope < 0 else "·")
        lines.append(f"  {direction} {name:<20s} {slope:+.4f}")
    lines.extend([
        "",
        "This shows which inputs move the reading at this point.",
        "It does not say which inputs should be changed.",
        "=" * 70,
    ])
    return "\n".join(lines)


# Demo
if __name__ == "__main__":
    from ..core.coherence_metric import PHI

    state = SystemState(
        resonance_energy=0.9,
        adaptability=0.85,
        diversity=0.8,
        coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
        loss_rate=0.1,
        energy_cost=6,
        description="Healthy coherent system",
    )
    print(format_sensitivity(sensitivity(state)))
