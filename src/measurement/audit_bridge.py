"""
Audit Bridge: standalone audits become M(S) inputs

The repository grew four audit subsystems — business resilience, refinery
dependency, premise validity, substrate awareness — that each measure
something real and none of which fed the core metric. They produced
their own verdicts in their own units and M(S) never saw them.

This module connects them. Each bridge takes the plain output of an audit
and returns a SystemState, so an audit can be read as a coherence
measurement rather than a separate opinion.

EVERY MAPPING IS AN ASSUMPTION, AND IT IS STATED
------------------------------------------------
There is no objectively correct way to say "workforce health *is* R_e".
Each bridge therefore carries a `notes` list naming the assumption behind
every term it assigns, and a `calibrations` list with the provenance of
anything derived through a published relationship. Disagree with a
mapping and you have a specific sentence to disagree with.

COUPLING AND THE INTERIOR OPTIMUM
---------------------------------
CoherenceMetric defaults to C* = I/phi, whose off-diagonal target is
zero — under that default, *any* coupling reduces f(C) monotonically and
there is no interior optimum to find. The bridges therefore supply an
explicit optimum with off-diagonal 1/phi^2 (see `phi_coupling_optimum`),
so that both an unconnected system and a rigidly over-connected one score
below a moderately connected one. That is the framework's stated design
(too weak = fragmented, too strong = rigid) made arithmetic.

MEASUREMENT, NOT CONTROL
------------------------
A bridge translates an audit into a reading. It does not rank the audited
system, recommend changes to it, or decide whether anything should be
replaced.
"""

from dataclasses import dataclass, field
from math import exp, log1p
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from ..core.coherence_metric import PHI, CoherenceMetric, SystemState
from .calibration import Calibration, A_from_recovery_events, D_response_diversity, \
    interdependence_penalty
from .coherence_verdict import CoherenceVerdict, assess

# Disruption levels used to probe a dependency graph for response
# diversity. A single 100%-loss probe cannot distinguish a component that
# degrades gracefully from one that fails at the first nudge.
STRESS_GRADIENT = (0.0, 0.25, 0.5, 0.75, 1.0)

# Perfectly synchronized responses give a synchrony index of 1 only up to
# floating-point error, so the "no viable alternatives" note is triggered
# by a tolerance rather than an exact comparison.
ZERO_TOLERANCE = 1e-9


@dataclass
class BridgedSystem:
    """An audit expressed as an M(S) measurement, with its assumptions."""

    state: SystemState
    metric: CoherenceMetric
    calibrations: List[Calibration] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def coherence(self) -> float:
        """M(S) for the bridged state."""
        return self.metric.calculate_from_state(self.state)

    def verdict(self, history: Optional[Sequence[float]] = None) -> CoherenceVerdict:
        """GREEN/AMBER/RED/BLACK verdict for the bridged state."""
        return assess(self.state, history=history, metric=self.metric)


def phi_coupling_optimum(n: int) -> np.ndarray:
    """Coupling optimum C* with a genuine interior maximum.

    Diagonal 1/phi (self-regulation), off-diagonal 1/phi^2 (cross-coupling
    one golden-ratio step weaker than self-coupling). Under this optimum a
    fully decoupled system and a rigidly coupled one are both penalized,
    which is what "optimal at intermediate coupling" has to mean if it
    means anything.
    """
    if n < 1:
        raise ValueError("coupling optimum needs at least one component")
    off = 1.0 / (PHI ** 2)
    C_star = np.full((n, n), off, dtype=float)
    np.fill_diagonal(C_star, 1.0 / PHI)
    return C_star


def coupling_matrix(n: int, cross_coupling: float) -> np.ndarray:
    """Symmetric coupling matrix with self-regulation 1/phi.

    Args:
        n: Number of components.
        cross_coupling: Off-diagonal interaction strength. Compare against
                        1/phi^2 ~ 0.382, the optimum used by these bridges.
    """
    if n < 1:
        raise ValueError("coupling matrix needs at least one component")
    C = np.full((n, n), float(cross_coupling), dtype=float)
    np.fill_diagonal(C, 1.0 / PHI)
    return C


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- Business resilience audit -------------------------------------------

# SPOF types from the business audit that describe *concentration* — the
# same capability resting on one point rather than several. These reduce
# viable strategies, so they are charged against D.
CONCENTRATION_SPOFS = frozenset({
    "supplier", "revenue_concentration", "knowledge_loss",
})


def from_business_audit(
    audit: Dict[str, Any],
    energy_cost: Optional[float] = None,
    description: Optional[str] = None,
) -> BridgedSystem:
    """Bridge `business_resilience_framework.full_audit` output into M(S).

    Mapping, with the assumption behind each term:

      R_e <- substrate_health.composite
          Constructive interaction flow is the workforce, knowledge and
          community substrate that actually produces capability. A firm
          whose substrate has been consumed has nothing left interacting
          constructively, whatever its revenue says.

      A   <- discretionary_effort.leading_indicator
          Discretionary effort is held-back capacity: the reserve a system
          deploys when it has to recover. The audit already treats it as
          a 6-18 month leading indicator of turnover, which is the
          behaviour of a recovery-rate term.

      D   <- substrate_health.knowledge, reduced by concentration SPOFs
          Cross-training and succession coverage are the viable ways the
          same work can get done. Concentration single-points-of-failure
          remove alternatives, so they are charged here.

      L   <- max(0, extraction_index - contribution_index)
          Value leaving the substrate faster than it returns is the loss
          rate, directly. A balanced or contributing firm has L = 0 from
          this channel — which does not mean it has no losses at all,
          only none this audit measured.

      f(C) <- cross-coupling raised above optimum by vulnerability_index
          Concentrated single points of failure are over-coupling: a
          shock anywhere propagates everywhere. Rigidity, not connection,
          is what the coupling term penalizes.

    Args:
        audit: Output of `full_audit(BusinessState)`.
        energy_cost: Optional energy denominator for the value ratio.
        description: Optional label; defaults to the audit's `name`.

    Returns:
        BridgedSystem carrying the state, metric, and stated assumptions.
    """
    try:
        substrate = audit["substrate_health"]
        extraction = audit["extraction_ratio"]
        cascade = audit["cascade_vulnerability"]
        effort = audit["discretionary_effort"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            "expected the output of business_resilience_framework.full_audit"
        ) from exc

    notes: List[str] = []

    r_e = _clamp01(float(substrate["composite"]))
    notes.append(
        f"R_e = substrate health composite ({r_e:.3f}) — assumes constructive "
        "flow is carried by the workforce/knowledge/community substrate"
    )

    a = _clamp01(float(effort["leading_indicator"]))
    notes.append(
        f"A = discretionary-effort leading indicator ({a:.3f}) — assumes "
        "held-back effort is the reserve a firm recovers with, and inherits "
        "that indicator's 6-18 month lead over turnover"
    )

    concentration = sum(
        float(s.get("weight", 0.0))
        for s in cascade.get("single_points_of_failure", [])
        if s.get("type") in CONCENTRATION_SPOFS
    )
    knowledge = _clamp01(float(substrate["knowledge"]))
    d = _clamp01(knowledge * (1.0 - _clamp01(concentration)))
    notes.append(
        f"D = knowledge depth {knowledge:.3f} reduced by concentration "
        f"single-points-of-failure ({concentration:.3f}) — counts ways the "
        "same work can still get done, not headcount"
    )
    if d <= ZERO_TOLERANCE:
        notes.append(
            "D reached zero: every alternative route is concentrated on one "
            "point. M(S) treats this as irreversible (BLACK), which is a "
            "strong claim — verify it against the underlying SPOF list."
        )

    loss = max(0.0, float(extraction["extraction_index"]) - float(extraction["contribution_index"]))
    l = _clamp01(loss)
    notes.append(
        f"L = extraction over contribution ({l:.3f}) — measures value leaving "
        "the substrate; other loss channels this audit does not see are absent "
        "from the reading, not absent from the firm"
    )

    vulnerability = _clamp01(float(cascade["vulnerability_index"]))
    cross = (1.0 / PHI ** 2) * (1.0 + vulnerability)
    notes.append(
        f"f(C): cross-coupling {cross:.3f} against optimum {1 / PHI ** 2:.3f} — "
        f"vulnerability index {vulnerability:.3f} read as over-coupling, since "
        "concentrated failure points propagate shocks system-wide"
    )

    state = SystemState(
        resonance_energy=r_e,
        adaptability=a,
        diversity=d,
        coupling_matrix=coupling_matrix(2, cross),
        loss_rate=l,
        energy_cost=energy_cost,
        description=description or audit.get("name"),
    )
    metric = CoherenceMetric(coupling_optimum=phi_coupling_optimum(2))
    return BridgedSystem(state=state, metric=metric, notes=notes)


# --- Refinery / dependency graph audit -----------------------------------


def _default_cascade(graph: Dict[str, Any], disrupted: Dict[str, float],
                     target: str) -> Dict[str, float]:
    """Load the dependency audit's own cascade propagation.

    Imported lazily and by reference rather than reimplemented, so the
    bridge cannot drift from the propagation logic it claims to bridge.
    """
    try:
        from dependency_audit.refinery_dependency_graph import cascade_disruption
    except ImportError as exc:  # pragma: no cover - depends on run location
        raise ImportError(
            "dependency_audit is not importable from here. Run from the "
            "repository root, or pass cascade_fn= explicitly."
        ) from exc
    return cascade_disruption(graph, disrupted, target)


def from_dependency_graph(
    graph: Dict[str, Any],
    target: str = "refined_output",
    cascade_fn: Optional[Callable[[Dict[str, Any], Dict[str, float], str],
                                  Dict[str, float]]] = None,
    energy_cost: Optional[float] = None,
    description: Optional[str] = None,
) -> BridgedSystem:
    """Bridge a dependency graph into M(S) by stress-probing it.

    Rather than reading the graph's declared attributes and calling them
    coherence, this probes the graph: each node is disrupted across a
    gradient and the target's surviving throughput is recorded. The
    response curves are the measurement.

      R_e <- mean surviving throughput under full single-node loss
          What constructive flow actually survives a typical shock,
          averaged over which node takes it.

      A   <- replacement times, via A_from_recovery_events
          replacement_time_days is literally a return time T_r, so the
          published T_r ~ 1/|lambda| relation applies without further
          assumption. This is the cleanest mapping in the module.

      D   <- response diversity of the per-node throughput curves
          If every node's failure produces the same collapse curve, the
          graph has one failure mode wearing many names. Response
          diversity (Elmqvist 2003) catches that; counting nodes does not.

      L   <- squashed mean brittleness, 1 - exp(-mean_brittleness)
          Brittleness is import_fraction x log(1+replacement_days), doubled
          for single points of failure. It is unbounded, so it is squashed
          into a rate. The squashing is a presentation choice with no
          empirical backing, and is flagged as such.

      f(C) <- mean degree, via the interdependent percolation threshold
          Buldyrev's 2.4554/<k> against the isolated 1/<k>.

    Args:
        graph: Mapping of node name to node, where each node has
               `depends_on`, `import_fraction`, `replacement_time_days`
               and `spof` attributes.
        target: Node whose throughput defines system output.
        cascade_fn: Propagation function; defaults to the dependency
                    audit's own `cascade_disruption`.
        energy_cost: Optional energy denominator for the value ratio.
        description: Optional label for the state.

    Returns:
        BridgedSystem carrying the state, metric, calibrations and notes.
    """
    if not graph:
        raise ValueError("dependency graph is empty")
    if target not in graph:
        raise ValueError(f"target node {target!r} is not in the graph")

    cascade = cascade_fn or _default_cascade
    notes: List[str] = []
    calibrations: List[Calibration] = []

    # Probe: one response curve per node, across the stress gradient.
    probes = [n for n in graph if n != target]
    curves: List[List[float]] = []
    full_loss_throughput: List[float] = []
    for node in probes:
        curve = []
        for level in STRESS_GRADIENT:
            result = cascade(graph, {node: level}, target)
            curve.append(float(result.get(target, 0.0)))
        curves.append(curve)
        full_loss_throughput.append(curve[-1])

    if not curves:
        raise ValueError("graph has no nodes other than the target to probe")

    r_e = _clamp01(sum(full_loss_throughput) / len(full_loss_throughput))
    notes.append(
        f"R_e = mean surviving throughput under full single-node loss "
        f"({r_e:.3f}) across {len(probes)} probes — assumes each node is "
        "equally likely to be the one that fails"
    )

    replacement_times = [
        float(getattr(node, "replacement_time_days", 0.0)) for node in graph.values()
    ]
    a_cal = A_from_recovery_events(replacement_times)
    calibrations.append(a_cal)
    notes.append(
        f"A = {a_cal.value:.3f} from replacement times via {a_cal.method} — "
        "replacement_time_days is a return time, so this mapping needs no "
        "extra assumption beyond the published T_r relation"
    )

    d_cal = D_response_diversity(curves)
    calibrations.append(d_cal)
    notes.append(
        f"D = {d_cal.value:.3f} response diversity across node-failure curves "
        f"(effective independent responses: "
        f"{d_cal.inputs.get('effective_independent_responses', float('nan')):.2f}) — "
        "identical collapse curves mean one failure mode, however many nodes"
    )
    if d_cal.value <= ZERO_TOLERANCE:
        notes.append(
            "D is effectively zero: every probe produced the same response curve, "
            "so M(S) reads BLACK. Check this against the propagation model "
            "before believing it — a conservative min-bottleneck cascade "
            "forces identical curves for every node in the target's "
            "dependency closure, so perfect synchrony can be a property of "
            "the model rather than of the system it describes."
        )

    brittleness = []
    for node in graph.values():
        score = float(getattr(node, "import_fraction", 0.0)) * log1p(
            float(getattr(node, "replacement_time_days", 0.0))
        )
        if getattr(node, "spof", False):
            score *= 2.0
        brittleness.append(score)
    mean_brittleness = sum(brittleness) / len(brittleness)
    l = _clamp01(1.0 - exp(-mean_brittleness))
    notes.append(
        f"L = {l:.3f} from mean brittleness {mean_brittleness:.3f}, squashed by "
        "1 - exp(-x). The squashing has no empirical backing; it converts an "
        "unbounded score into a rate and nothing more."
    )

    edges = sum(len(getattr(node, "depends_on", []) or []) for node in graph.values())
    mean_degree = edges / len(graph)
    if mean_degree > 0:
        c_cal = interdependence_penalty(mean_degree, coupled_fraction=1.0)
        calibrations.append(c_cal)
        cross = _clamp01(c_cal.inputs["effective_pc"])
        notes.append(
            f"f(C): cross-coupling {cross:.3f} from the interdependent "
            f"percolation threshold at mean degree {mean_degree:.2f} — note "
            "this transition is first-order, so L offers no advance gradient"
        )
    else:
        cross = 0.0
        notes.append(
            "f(C): graph has no edges; cross-coupling set to zero, which the "
            "phi optimum reads as fragmented rather than healthy"
        )

    state = SystemState(
        resonance_energy=r_e,
        adaptability=a_cal.value,
        diversity=d_cal.value,
        coupling_matrix=coupling_matrix(2, cross),
        loss_rate=l,
        energy_cost=energy_cost,
        description=description or f"dependency graph -> {target}",
    )
    metric = CoherenceMetric(coupling_optimum=phi_coupling_optimum(2))
    return BridgedSystem(state=state, metric=metric,
                         calibrations=calibrations, notes=notes)


def format_bridge(b: BridgedSystem) -> str:
    """Human-readable rendering of a bridged audit, assumptions included."""
    s = b.state
    lines = [
        "=" * 70,
        f"BRIDGED AUDIT: {s.description or 'unnamed system'}",
        "=" * 70,
        f"  R_e = {s.resonance_energy:.4f}",
        f"  A   = {s.adaptability:.4f}",
        f"  D   = {s.diversity:.4f}",
        f"  f(C)= {b.metric.coupling_function(s.coupling_matrix):.4f}",
        f"  L   = {s.loss_rate:.4f}",
        f"  M(S)= {b.coherence():+.4f}",
    ]
    verdict = b.verdict()
    lines.append(f"  signal = {verdict.signal}")
    if b.notes:
        lines.append("")
        lines.append("MAPPING ASSUMPTIONS:")
        for n in b.notes:
            lines.append(f"  - {n}")
    if b.calibrations:
        lines.append("")
        lines.append("CALIBRATION SOURCES:")
        for c in b.calibrations:
            lines.append(f"  - {c.term}: {c.source}")
    lines.extend([
        "",
        "An audit read as coherence is still the audit's opinion, restated.",
        "=" * 70,
    ])
    return "\n".join(lines)


# Demo
if __name__ == "__main__":
    from business_audit.business_resilience_framework import full_audit, reference_profiles
    from dependency_audit.refinery_dependency_graph import build_us_refinery_graph

    for profile in reference_profiles():
        bridged = from_business_audit(full_audit(profile), energy_cost=None)
        print(format_bridge(bridged))
        print()

    graph_bridge = from_dependency_graph(build_us_refinery_graph())
    print(format_bridge(graph_bridge))
