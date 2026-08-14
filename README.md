# Mathematical Collapse-Prevention Model (MCPM)

**Truth-Telling Through Systemic Coherence Measurement**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## What This Does

Measures systemic health through coherence metrics integrated with energy
accounting.

**This framework MEASURES reality. It does NOT control systems.**

### Core Measurement

```
M(S) = (R_e × A × D × f(C)) - L
```

| Term | Meaning |
|---|---|
| `R_e` | Resonance energy (constructive interaction) |
| `A` | Adaptability (recovery rate) |
| `D` | Diversity (viable strategies) |
| `f(C)` | Coupling function (optimal at intermediate values) |
| `L` | Loss / entropy rate |

```
Value = M(S) / Energy_Cost
```

The gain term is multiplicative, so any one of `R_e`, `A` or `D` reaching
zero takes the whole product to zero. That is deliberate: a system with no
remaining viable strategies is not partially healthy, and the verdict
layer reports it as `BLACK` — irreversible from within.

With one caveat the formula cannot see on its own: M(S) measures flux,
and a *dormant* system reads zero too. See
[Dormancy](#dormancy-ms-cannot-tell-waiting-from-dying).

## Use Cases

**Truth-telling (what this is for)**

- Show what a system's coherence actually is, from measured data
- Reveal hidden energy costs
- Compare what different arrangements cost and produce
- Watch a monitored series for the approach to a tipping point

**Control (what this is not for)**

- Optimizing populations toward the metric
- Enforcing conformity to "coherence"
- Applying interventions without consent
- Social engineering

The distinction is not decorative. See
[docs/TRUTH_TELLING.md](docs/TRUTH_TELLING.md) for why measurement and
control are kept apart, and why targeting this metric would destroy it
(Goodhart's law, Campbell's law).

## Installation

```bash
git clone https://github.com/JinnZ2/Mathematical-collapse-prevention-model.git
cd Mathematical-collapse-prevention-model
pip install -e .
```

Requires Python 3.8+ and numpy. The measurement modules for early
warning, calibration and forecast auditing are standard library only.

## Quick Start

```python
import numpy as np
from src.core.coherence_metric import CoherenceMetric, SystemState
from src.measurement.coherence_verdict import assess, format_verdict

state = SystemState(
    resonance_energy=0.9,
    adaptability=0.85,
    diversity=0.8,
    coupling_matrix=np.array([[0.618, 0.3], [0.3, 0.618]]),
    loss_rate=0.1,
    energy_cost=6,          # kWh/day — enables the value ratio
    description="Example system",
)

metric = CoherenceMetric()
print(metric.calculate_from_state(state))     # M(S)
print(metric.efficiency_ratio(state))         # M(S) / energy_cost
print(format_verdict(assess(state)))          # GREEN / AMBER / RED / BLACK
```

### Where the numbers come from

Supplying the five terms by hand is honest but unfalsifiable. The
calibration adapters derive them from measured data instead, and each one
returns its source and caveats with the number:

```python
from src.measurement.calibration import A_from_timeseries, D_response_diversity

A = A_from_timeseries(monitored_series)     # recovery rate from lag-1 autocorrelation
print(A.value, A.source, A.caveats)

D = D_response_diversity([                  # response diversity, not headcount
    component_a_under_stress,
    component_b_under_stress,
])
```

### Dormancy: M(S) cannot tell waiting from dying

M(S) measures *flux*. A dormant system and a dead one both read
`R_e = A = D = 0`, and the verdict layer calls both BLACK. For a
collapsed system that is right. For a seed, a spore, or a tardigrade in
tun state it is a false positive — anhydrobiotic tardigrades suspend
metabolism and resume; Judean date palm seeds have germinated after
~2000 years. **No flux measurement can separate those cases, because
during dormancy there is no flux to measure.**

`dormancy` supplies the structural channel instead:

```python
from src.measurement.dormancy import fold, fold_window, assess_dormancy, format_dormancy

print(fold_window(resonance_energy=0.10).open)   # False — too late to fold

seed = fold(resonance_energy=0.40, adaptability=0.30,
            diversity=0.55, coupling=0.70, residual_activity=0.04)
print(format_dormancy(assess_dormancy(seed, periods_elapsed=500)))
```

A seed keeps *proportions*, not magnitude — it is the structure at
minimum energy, so it can re-expand at whatever scale the world later
allows. Three things stop this from being wishful:

- **Folding costs energy**, so the option closes while the system is
  still alive. `fold_window` reports that closing; below the cost, the
  choice to wait is simply gone.
- **Preservation decays on a clock.** Longevity follows the Ellis &
  Roberts viability equation (1980, *Annals of Botany* 45:13); across
  the stress range its time constant runs from ~56,000 periods down to
  ~96.
- **Over-compression destroys the seed.** Below roughly 2% residual
  activity, further compression buys no longevity and damages what is
  being preserved.

`assess_dormancy(None)` returns `NEVER_FOLDED` and says so plainly: a
missing seed is absent evidence, not proof of death.

### Where the coupling optimum comes from

`f(C)` is supposed to peak at intermediate coupling — "too weak =
fragmented, too strong = rigid." Implemented as a bump around a chosen
`C*`, that is an assertion: move `C*` and the optimum moves with it.
Synchronization theory derives the same shape with no free parameter.

For units coupled through a network, the synchronous state is stable
exactly when every scaled Laplacian eigenvalue lands inside the Master
Stability Function's negative region, `ν₁ < σλᵢ < ν₂`
([Pecora & Carroll 1998](https://doi.org/10.1103/PhysRevLett.80.2109)):

```python
import numpy as np
from src.measurement.coupling_physics import MSFWindow, coupling_coherence, format_coupling

window = MSFWindow(nu_lower=0.2, nu_upper=4.0)   # measured from your node dynamics
ring = np.array([[0,1,0,0,1],[1,0,1,0,0],[0,1,0,1,0],[0,0,1,0,1],[1,0,0,1,0]], float)

print(format_coupling(coupling_coherence(0.4, ring, window)))
```

Three things fall out that the bump form cannot express:

- **The interior optimum is a property of the dynamics, not a law.**
  [Huang et al. 2009](https://doi.org/10.1103/PhysRevE.80.036204) prove
  only three MSF classes are possible. Only Class III has a bounded
  window; Class II has a threshold and no upper penalty at all. This
  module reports the class instead of assuming a peak exists.
- **Fragmentation is structural, not mistuning.** A disconnected network
  has `λ₂ = 0`, so *no* coupling strength synchronizes it. That is a
  different failure from being undercoupled, and it is reported as one.
- **Some networks cannot be fixed by tuning.** Both bounds are
  satisfiable only when `λ_N/λ₂ < ν₂/ν₁`
  ([Barahona & Pecora 2002](https://doi.org/10.1103/PhysRevLett.89.054101))
  — topology on the left, dynamics on the right. Above that, the remedy
  is a different network, not a different coupling strength.

### How much does the reading actually determine?

M(S) returns one number with no error bar, and that number reads as
precise. Because the gain term is a product, five uncertain inputs
compound into a result far less determined than it looks:

```python
from src.measurement.uncertainty import Interval, UncertainState, propagate, format_uncertainty

state = UncertainState(
    resonance_energy=Interval(0.60, 0.90),
    adaptability=Interval(0.50, 0.90),
    diversity=Interval(0.50, 0.90),
    coupling=Interval(0.75, 0.95),
    loss_rate=Interval(0.15, 0.35),
)
print(format_uncertainty(propagate(state)))
```

Those inputs give a point estimate of `M(S) = +0.06` — GREEN. The
propagated interval is `[-0.24, +0.54]`, and the verdict comes back
**UNDETERMINED**: the same evidence is consistent with RED. The bounds
are exact rather than sampled, since M(S) is monotone in every input.

`monte_carlo` adds what intervals cannot — `P(M(S) < 0)` and the
probability mass per signal — at the cost of assuming a distribution
shape and independence between inputs. Both assumptions are stated in
its output, because independence is the one most likely to be wrong:
the stress that drains `R_e` usually erodes `A` and `D` too.

### Watching for a tipping point

A system approaching a transition recovers from perturbations more and
more slowly, and that shows up in a monitored series before the
transition does:

```python
from src.measurement.early_warning import critical_slowing_down, format_reading

print(format_reading(critical_slowing_down(monitored_series)))
```

Flags are `CRITICAL_SLOWING_DOWN`, `PARTIAL_SIGNAL`, `NO_SIGNAL` or
`INSUFFICIENT_DATA`. On the module's own synthetic benchmarks, ~75% of
genuinely eroding systems raise a flag and ~8% of stationary ones do.
**No signal is not evidence of safety** — roughly a third of real
transitions give no advance warning at all, and abruptly-failing coupled
systems give none by construction. The module says so in its own output.

## Repository Structure

```
├── src/
│   ├── core/
│   │   ├── coherence_metric.py        # M(S) formula
│   │   └── golden_ratio_trust.py      # trust emergence (φ-ratio chambers)
│   └── measurement/
│       ├── audit_bridge.py            # audits -> M(S) inputs
│       ├── ai_forecast_audit.py       # forecast accuracy + compute burden
│       ├── calibration.py             # cited derivations of R_e/A/D/L
│       ├── coherence_verdict.py       # GREEN/AMBER/RED/BLACK signal layer
│       ├── coupling_physics.py        # f(C) optimum from synchronization stability
│       ├── dormancy.py                # fold to a seed; dormancy vs death
│       ├── early_warning.py           # critical slowing down, rate tipping
│       ├── empathy_types.py           # empathy paradigm comparison
│       ├── multi_model_peer_review.py # AI-to-AI cross-validation
│       ├── replacement_analysis.py    # replacement thermodynamics
│       ├── sensitivity.py             # ∂M/∂x per input
│       ├── uncertainty.py             # interval + Monte Carlo propagation
│       └── validation_timeline_audit.py
├── legacy/                            # work that came first, still live
│   ├── business_audit/                # business resilience self-audit
│   ├── dependency_audit/              # refinery dependency graph
│   ├── premise_audit/                 # cross-domain premise validity
│   ├── substrate_audit/               # substrate-aware audit
│   └── Meta-Framework-Note.md         # origin-era note
├── examples/                          # worked scenarios
├── docs/
│   ├── TRUTH_TELLING.md               # measurement vs control
│   └── FALSIFICATION_LOG.md           # what broke, and what replaced it
└── tests/                             # stdlib unittest suites
```

`legacy/` is a **precedence record, not a graveyard.** Everything in it
still imports, still runs, and is still exercised by the test suite. It
holds the standalone tools that predate `src/`, each with the date it
first appeared and what carries its work now — see
[`legacy/README.md`](legacy/README.md).

Every module has a runnable demo:

```bash
python -m src.core.coherence_metric
python -m src.measurement.early_warning
python -m src.measurement.calibration
python -m src.measurement.coupling_physics
python -m src.measurement.dormancy
python -m src.measurement.uncertainty
python -m src.measurement.audit_bridge
```

## Examples

[`examples/run_community_year.py`](examples/run_community_year.py) walks a
small rural community through twelve months of erosion, printing the
signal trajectory month by month:

```bash
python -m examples.run_community_year
```

Run from the repository root, as a module — the script imports `src`,
which is only on the path from there.

## Tests

Stdlib `unittest`, no external runner. The suites are *falsifiable*: each
test pins a claim the framework makes, so a broken claim fails a test.

```bash
python -m unittest discover -v tests
```

Run from the repository root — the audit-bridge tests import the packages
under `legacy/` as namespace packages.

## How the framework revises itself

Hypothesize, run, watch the result falsify the claim, edit the claim,
look for what is still unknown, rerun. The code only ever shows the last
step of that loop, and a claim that survived a test looks identical to
one that was never tested. So the rest of the loop is written down:
[`docs/FALSIFICATION_LOG.md`](docs/FALSIFICATION_LOG.md).

Eight claims this framework made and then broke, each with the run that
broke it, including:

- **A single M(S) number is a reading.** Falsified by propagating input
  ranges: a point estimate of `+0.06` (GREEN) sits inside an interval of
  `[−0.24, +0.54]` that is equally consistent with RED. → `uncertainty.py`
- **Zero flux means dead.** Falsified by cryptobiosis — a tardigrade in
  tun state reads exactly like a corpse, and *no flux measurement can fix
  that*, because during dormancy there is no flux to measure. →
  `dormancy.py`
- **The coupling optimum sits at C\* = I/φ.** Falsified twice: the
  default's off-diagonal target is zero, so there is no interior optimum
  at all — and a bump around any chosen `C*` is an assertion, since
  moving `C*` moves the optimum. → `coupling_physics.py`

Plus rejected alternatives that never shipped but are worth not
reinventing — a bare `|τ| ≥ 0.5` early-warning threshold fires on **45%
of stationary series** that are approaching nothing, because overlapping
rolling windows autocorrelate the indicator.

The log ends with a **Never tested** section listing the claims still
standing on nothing at all. That section is the point of the exercise: a
framework that reports absent evidence as absent has to apply the rule to
itself first.

## Important Distinctions

**This framework is:** a measurement tool, a diagnostic, an efficiency
calculator, a pattern descriptor.

**This framework is not:** a control system, an optimization target, a
social engineering tool, an intervention system.

Measure reality. Don't enforce ideology.

## Contributing

Contributions must preserve the measurement focus and never add control
mechanisms — no optimization loops, no intervention logic, no enforcement.
Adding a measurement means stating its assumptions in its own output.

## License

MIT — see [LICENSE](LICENSE).

Note that MIT permits proprietary use. If preventing proprietary capture
matters more than permissive reuse, that is a licensing decision to
revisit deliberately rather than a gap to patch.

## Citation

```bibtex
@software{mcpm,
  title  = {Mathematical Collapse-Prevention Model},
  author = {JinnZ2},
  url    = {https://github.com/JinnZ2/Mathematical-collapse-prevention-model}
}
```

---

> "Energy accounting proves WHO is efficient. Geometric morality proves
> HOW to collaborate. Together: Complete truth-telling."
