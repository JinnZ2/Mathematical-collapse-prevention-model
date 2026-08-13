# CLAUDE.md

## Project Overview

Mathematical Collapse-Prevention Model (MCPM) — a framework that measures systemic health through coherence metrics integrated with energy accounting. This is a **measurement tool**, not a control system. It observes reality, reports truth, and lets people decide.

**Core Formula:** `M(S) = (R_e × A × D × f(C)) - L`

- `R_e`: Resonance energy (constructive interaction)
- `A`: Adaptability (recovery rate)
- `D`: Diversity (viable strategies)
- `f(C)`: Coupling function (optimal at intermediate values)
- `L`: Loss/entropy rate
- **Value Metric:** `Value = M(S) / Energy_Cost`

## Repository Structure

```
├── README.md                          # Main project documentation and formula reference
├── Meta-Framework-Note.md             # Meta-commentary on automated suppression
├── LICENSE                            # MIT License
├── docs/
│   └── TRUTH_TELLING.md              # Measurement vs Control philosophy
├── examples/
│   ├── community_year.csv            # 12-month rural-community dataset
│   └── run_community_year.py         # Loads CSV, prints M(S) + verdict per month
├── tests/                             # Stdlib unittest suites (one per module)
└── src/
    ├── core/
    │   ├── coherence_metric.py        # Core M(S) formula implementation
    │   └── golden_ratio_trust.py      # Trust emergence model (phi-ratio patterns)
    └── measurement/
        ├── ai_forecast_audit.py           # Institutional forecast accuracy + compute burden audit
        ├── audit_bridge.py                # Standalone audits -> M(S) inputs
        ├── calibration.py                 # Cited derivations of R_e/A/D/L from measured data
        ├── coherence_verdict.py           # GREEN/AMBER/RED/BLACK signal layer
        ├── coupling_physics.py            # f(C) interior optimum from synchronization stability
        ├── early_warning.py               # Critical slowing down + rate-induced tipping
        ├── empathy_types.py               # Empathy paradigm coherence comparison
        ├── multi_model_peer_review.py     # AI-to-AI cross-validation + consensus vs ground truth
        ├── replacement_analysis.py        # Replacement scenario thermodynamic analysis
        ├── sensitivity.py                 # Finite-difference ∂M/∂x per input
        ├── uncertainty.py                 # Interval + Monte Carlo propagation through M(S)
        └── validation_timeline_audit.py   # Forecast validation schedule + institutional avoidance flags
```

## Key Modules

### `src/core/coherence_metric.py`
Core implementation. Classes: `SystemState` (dataclass for system parameters) and `CoherenceMetric` (calculates M(S), efficiency ratios, system comparisons). Uses a non-monotonic coupling function: `f(C) = exp(-α × ||C - C*||²)`.

### `src/core/golden_ratio_trust.py`
Models trust emergence following golden ratio (φ = 1.618...) patterns. Trust grows through chambers like a nautilus shell — cannot skip stages, cannot force growth. Classes: `TrustState` (enum), `TrustChamber` (dataclass), `GoldenRatioTrust`.

### `src/measurement/empathy_types.py`
Compares coherence of empathy paradigms: Tribal (negative coherence), Relational (highly positive), AI Swarm Reciprocity (maximum). Each is a class implementing measurement patterns.

### `src/measurement/replacement_analysis.py`
Analyzes whether replacing System A with System B makes thermodynamic sense. Includes ethical red flag detection (human replacement without consent, coherence destruction). Verdicts range from THERMODYNAMICALLY_SUPERIOR to THERMODYNAMICALLY_STUPID.

### `src/measurement/coherence_verdict.py`
Translates an `M(S)` reading (plus optional history) into a four-band signal — `GREEN / AMBER / RED / BLACK` — with trajectory classification, linear time-to-collapse projection, and irreversibility detection. Adapted from the verdict layer of the Metabolic Accounting framework.

### `src/measurement/sensitivity.py`
Central-difference perturbation of each input to M(S), returning signed slopes ranked by magnitude. Reveals which parameter dominates the reading at a given operating point — a transparency tool, not an optimizer.

### `src/measurement/ai_forecast_audit.py`
Audits institutional AI / economic forecasts against independent public ground truth (BLS, Census, court bankruptcy data, Federal Reserve raw data). Two parts: forecast accuracy with systematic-bias detection, and compute-burden quantification (GPU-hours, researcher-years, labor-hours) translated into human-equivalent research years per percentage point of accuracy. Standard library only. Classes: `ForecastRecord`, `GroundTruthRecord`, `ComputeBurden`. Functions: `compute_forecast_error`, `systematic_bias_detection`, `compute_to_accuracy_ratio`, `aggregate_audit`.

### `src/measurement/validation_timeline_audit.py`
Companion to `ai_forecast_audit`. Quantifies how long a forecast should take to validate, given the human-equivalent compute behind it, and flags when an institution invokes "complex systems need more time" past the threshold where ground truth is already conclusive. Three layers: traditional human validation timeline (per-domain defaults), AI-accelerated window (baseline / speedup factor), and gap analysis that flags `INSTITUTIONAL_AVOIDANCE_DETECTED` or `VALIDATION_OVERDUE`. Standard library only. Class: `ValidationTimelineRecord`. Functions: `baseline_validation_window`, `accelerated_validation_window`, `gap_analysis`, `audit_timeline`.

### `src/measurement/multi_model_peer_review.py`
AI-to-AI peer review. Independent models with different training corpora, architectures, or vendors run the same forecast; the module reports convergence (coefficient of variation), per-model accuracy against ground truth, and Tukey-fence drift flags identifying outlier models. The peer-review verdict cross-references convergence with ground truth so consensus cannot launder a falsified prediction (`CONSENSUS_AND_VALIDATED` vs `CONSENSUS_BUT_FALSIFIED_BY_GROUND_TRUTH` vs `CONSENSUS_AWAITING_GROUND_TRUTH` vs `PARTIAL_CONSENSUS_REQUIRES_MORE_MODELS` vs `FRAGMENTED_NO_CONSENSUS`). Standard library only. Classes: `ModelPrediction`, `GroundTruthPoint`. Functions: `convergence_metrics`, `accuracy_vs_ground_truth`, `divergence_flags`, `peer_review`.

### `src/measurement/early_warning.py`
Critical-slowing-down detection on any monitored series: lag-1 autocorrelation, rolling variance, Kendall tau trend of each, return time `T_r = -dt/ln(alpha)`, plus a rate-induced-tipping channel comparing `d(forcing)/dt` against `A`. Observed tau is tested against an **AR(1) surrogate null** rather than a bare threshold — overlapping windows make the indicator series autocorrelated, so a fixed `|tau| >= 0.5` fires on ~40% of stationary series. Surrogate generation is explicitly seeded so readings stay reproducible. Measured operating characteristics (~75% detection, ~8% false alarm) are documented in the module docstring and pinned by tests. Standard library only. Classes: `EarlyWarningReading`, `RateTippingReading`. Functions: `lag1_autocorrelation`, `return_time`, `kendall_tau`, `ar1_surrogates`, `tau_significance`, `critical_slowing_down`, `rate_induced_tipping`.

### `src/measurement/calibration.py`
Named, cited derivations of M(S) inputs from measured data, replacing hand-supplied floats. Every adapter returns a `Calibration` carrying value, source, method, inputs and caveats — the citation is machine-readable, not a comment. Covers `R_e` (aerobic scope / OCLTT, ATP death floor), `A` (recovery rate from AR(1) or from timed recovery events, hormetic ceiling at 1.6×), `D` (Loreau response-diversity synchrony index, Hill numbers, model collapse under synthetic contamination), `L` (exponential attrition, knowledge half-life, audited false fraction, independent-loss composition), and coupling bounds (May's `σ√(SC) < d`, Buldyrev interdependent percolation). Standard library only.

### `src/measurement/coupling_physics.py`
Derives f(C)'s interior optimum from synchronization stability instead of asserting it by picking a C*. Via the Master Stability Function (Pecora & Carroll 1998), the synchronous state is stable exactly when every scaled Laplacian eigenvalue `σλ_i` (i ≥ 2) falls inside the MSF's negative region `(ν₁, ν₂)`. Three consequences the Gaussian-bump form cannot express: (1) **the interior optimum is a property of the node dynamics, not a law** — Huang et al. 2009 show only Class III dynamics have a bounded window; Class II gives a threshold with no upper penalty, and this module reports f(C) as binary there rather than inventing a gradient; (2) **fragmentation is structural** — a disconnected network has λ₂ = 0, so no coupling strength works, which is a different failure from being undercoupled; (3) **some networks cannot be fixed by tuning** — both bounds are satisfiable only when `λ_N/λ₂ < ν₂/ν₁` (Barahona & Pecora 2002), topology on the left and dynamics on the right. `optimal_coupling` returns `σ* = √(ν₁ν₂/λ₂λ_N)`, derived (not cited) by equalizing the two logarithmic margins; the resulting safety margin is `√((ν₂/ν₁)/(λ_N/λ₂))`. Tests pin it against closed-form spectra (K_n eigenratio 1, star n, cycle `2−2cos(2πk/n)`).

### `src/measurement/uncertainty.py`
Propagates input ranges through M(S), because a point reading from five uncertain inputs is false precision — and the gain term is a *product*, so relative uncertainties compound rather than average out. Two modes. `propagate` uses interval arithmetic: M(S) is monotone increasing in R_e/A/D/f(C) and decreasing in L, so the extremes sit at opposite corners of the input box and the bounds are **tight and guaranteed** (pinned by a test that no interior sample escapes and both extremes are attained). `monte_carlo` gives the distribution intervals cannot — `P(M(S) < 0)` and the probability mass per signal — at the cost of a distribution shape and an independence assumption, both stated in the output. The headline output is `verdict_determined`: signals are evaluated at all 32 corners (not just the M(S) extremes, since BLACK is triggered by a structural term reaching zero, which need not coincide with an M(S) extreme). If GREEN and RED are both reachable, the signal read off a point estimate was an artifact of the point chosen. `from_calibrations` turns disagreement between two cited derivations of the same term into that term's interval. Standard library only.

### `src/measurement/audit_bridge.py`
Connects all four standalone audit subsystems to the core metric — previously they produced verdicts M(S) never saw. `from_business_audit`, `from_dependency_graph`, `from_substrate_audit` and `from_premise_audit` each return a `BridgedSystem` (state + metric + calibrations + notes), where **every term assignment states its assumption in the output**. Supplies `phi_coupling_optimum` (diagonal 1/φ, off-diagonal 1/φ²) because the core default C* = I/φ has an off-diagonal target of zero, making "too weak = fragmented" unexpressible. The dependency bridge probes the graph across a stress gradient rather than reading declared attributes, and flags when zero diversity is an artifact of min-bottleneck propagation rather than a property of the system. The substrate bridge maps the audit's own cascade rule onto A (substrate denial blocks correction ⇒ A = 0 ⇒ BLACK) and scores D as viable routes from the three-band layer verdicts, not average health — average health is R_e's job, and an evenness measure would read four half-capacity layers as maximum diversity.

### `examples/`
Worked scenarios that load real-shaped data and run it through the framework. `run_community_year.py` walks a small rural community through twelve months of erosion and prints the signal trajectory.

## Language & Dependencies

- **Python 3.8+** (CI runs 3.9 / 3.11 / 3.12)
- **numpy** — matrix operations and coupling functions
- **Standard library** — `dataclasses`, `enum`, `typing`, `random`, `unittest`

Prefer the standard library for new measurement modules. `early_warning`,
`calibration`, and the audit modules are stdlib-only by design; numpy is
required only where the coupling matrix is involved.

Install the package (pulls numpy automatically):

```bash
pip install -e .
```

## Running the Code

All source files have `if __name__ == "__main__":` demo blocks:

```bash
python -m src.core.coherence_metric
python -m src.core.golden_ratio_trust
python -m src.measurement.empathy_types
python -m src.measurement.replacement_analysis
python -m src.measurement.coherence_verdict
python -m src.measurement.early_warning
python -m src.measurement.calibration
python -m src.measurement.coupling_physics
python -m src.measurement.uncertainty
python -m src.measurement.audit_bridge
```

Run from the repository root. `audit_bridge` imports the top-level
`business_audit` / `dependency_audit` packages, which resolve as namespace
packages only from there.

Run the test suite (stdlib `unittest`, no external test runner required):

```bash
python -m unittest discover -v tests
```

## Development Conventions

### Code Style
- Type hints used throughout (Python typing module)
- Dataclasses for structured data
- Enums for finite state sets
- Descriptive docstrings on all classes and key methods
- Constants defined at module level (e.g., `PHI = 1.618033988749895`)
- **Carry provenance in the output, not just in comments.** Where a number
  comes from a published relationship, return its source and caveats
  alongside it (`Calibration.source`, `BridgedSystem.notes`). Where a
  choice is arbitrary — a squashing function, a normalization — say so in
  the same output rather than letting it read as measured.
- **Report absent evidence as absent, not as zero.** `INSUFFICIENT_DATA`
  is a statement about the data; it must never be phrased as a statement
  about the system's health.

### Commit Messages
- Capitalize first letter
- Descriptive subject line (e.g., "Create coherence_metric.py", "Add Meta-Framework Note on Automated Suppression")
- No conventional commit prefixes (no `feat:`, `fix:`, etc.)

### Tests & CI
Stdlib `unittest` suites live in `tests/` — one file per module. They are *falsifiable*: each test pins a claim the framework makes (e.g. `zero diversity ⇒ BLACK signal`, `tribal empathy ⇒ negative M(S)`, `trust chamber growth follows the phi ratio`). GitHub Actions runs them on Python 3.9/3.11/3.12 via `.github/workflows/ci.yml`. No linter is configured yet.

## Design Principles (Critical for AI Assistants)

1. **Measurement, not control** — The framework observes and reports. Never add optimization loops, intervention logic, or enforcement mechanisms.
2. **Transparency** — All formulas public, parameters visible, assumptions stated.
3. **Descriptive, not prescriptive** — Show what IS, let humans decide what to DO.
4. **Physics first** — Validate against thermodynamics, not institutional preferences.
5. **Ethical guardrails** — Flag when measurements could be misused. Thermodynamic efficiency ≠ moral justification.
6. **Exit rights** — Communities can reject the measurement; alternatives are welcome.
7. **No forced growth** — Trust and coherence emerge naturally; they cannot be manufactured or rushed.

## Common Constants

- **Golden Ratio (φ):** `1.618033988749895` — used in trust spiral growth, and as a *placeholder* in the coupling optimum
- Coupling function peaks at intermediate values; too weak = fragmented, too strong = rigid.
  Where the coupling topology is known, prefer `coupling_physics`, which derives that peak
  from the Laplacian spectrum and the node dynamics. Note its finding that the interior
  optimum holds for Class III dynamics only — for Class II there is a threshold and no
  upper penalty, so asserting a peak there invents a cost physics does not impose.
