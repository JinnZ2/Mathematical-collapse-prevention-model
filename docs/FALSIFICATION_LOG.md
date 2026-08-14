# Falsification Log

The loop this repository runs on:

> hypothesize → run → result falsified → edit the claim → search for what
> is still unknown → rerun

The current code shows only the last step of that loop. This file keeps
the rest of it, because a claim that survived a test and a claim that was
never tested look identical once they are written down. The difference is
the whole point of the framework, so it is recorded rather than lost to
git history.

Two kinds of entry, kept apart because they carry different weight:

- **[FALSIFIED]** — the claim shipped, was run, and broke. The revision
  was forced.
- **[REJECTED]** — the obvious approach was tested and did not survive
  the test, so it never shipped. Weaker than a falsification of live
  code, but stronger than a design preference, and reproducible.

Every entry ends with **Still open**, which is the "search for unknowns"
step. If that section is empty, the entry is not finished.

---

## F-1 · Five hand-supplied floats are an honest input

**[FALSIFIED]** · claimed 2025-11-27 (`a154de4`) · revised 2026-08-13 (`a33657b`)

**Claim.** `M(S) = (R_e × A × D × f(C)) − L`, with the five terms supplied
by the analyst as floats in [0, 1].

**Run.** Try to state what observation would refute a given reading.

**Result.** There is none. Any M(S) can be produced by choosing inputs, so
the formula makes no refutable prediction — it is a restatement of the
analyst's prior in five decimal places. The arithmetic was never wrong;
it was unfalsifiable, which is worse.

**Revised claim.** `src/measurement/calibration.py`. Each adapter derives
a term from measured data and returns a `Calibration` carrying value,
source, method, inputs and caveats — the citation is machine-readable,
not a comment. `R_e` from aerobic scope / OCLTT and the ATP death floor;
`A` from AR(1) recovery rate or timed recovery events (hormetic ceiling
1.6×); `D` from Loreau response-diversity synchrony or Hill numbers; `L`
from exponential attrition, knowledge half-life, or audited false
fraction.

**Still open.**
- Coverage is partial. Many systems have no published relationship to
  calibrate against, and for those the terms are still hand-supplied —
  the log entry above applies to them in full.
- The adapters' constants were measured in specific domains. Applying a
  seed-viability or fish-metabolism constant to an institution is an
  analogy, not a measurement. Each adapter says so; nothing enforces it.

---

## F-2 · The coupling optimum sits at C\* = I/φ

**[FALSIFIED]** · claimed 2025-11-27 (`a154de4`) · revised 2026-08-13 (`a33657b`, `f45f574`)

**Claim.** `f(C) = exp(−α‖C − C*‖²)` peaks at intermediate coupling — too
weak is fragmented, too strong is rigid — with the default `C* = I/φ`.

**Run.** Bridge the four standalone audits into M(S) and read f(C) across
a range of cross-coupling values.

**Result.** Falsified twice over.

1. `C* = I/φ` is diagonal, so its **off-diagonal target is zero**. Under
   that default *any* cross-coupling reduces f(C) monotonically. There is
   no interior optimum at all, and "too weak = fragmented" is not merely
   mis-located — it is inexpressible.
2. More generally, a bump around a chosen `C*` is an assertion, not a
   measurement. Move `C*` and the optimum moves with it. Nothing in the
   model says where to put it.

**Revised claim.** Two layers, deliberately not merged.

- `audit_bridge.phi_coupling_optimum` — off-diagonal `1/φ²`, so an
  interior maximum exists. **Labelled a placeholder in its own
  docstring**: nothing in the stability literature puts the optimum at
  `1/φ²`. Used only when an audit hands over a scalar, which has no
  spectrum to work with.
- `src/measurement/coupling_physics.py` — the real answer. Via the Master
  Stability Function (Pecora & Carroll 1998), the synchronous state is
  stable exactly when every scaled Laplacian eigenvalue `σλᵢ` (i ≥ 2)
  falls in `(ν₁, ν₂)`. `optimal_coupling` returns
  `σ* = √(ν₁ν₂ / λ₂λ_N)`, derived by equalizing the two logarithmic
  margins — **no free parameter**.

Three consequences the bump form could not express, each a finding in its
own right:

- **The interior optimum is a property of the node dynamics, not a law.**
  Huang et al. 2009 prove only three MSF classes exist. Only Class III
  has a bounded window. Class II has a threshold and *no upper penalty*,
  so `coupling_physics` reports f(C) as binary there rather than
  inventing a cost physics does not impose.
- **Fragmentation is structural.** A disconnected network has `λ₂ = 0`, so
  no coupling strength synchronizes it — a different failure from being
  undercoupled, and reported as one.
- **Some networks cannot be tuned at all.** Both bounds are satisfiable
  only when `λ_N/λ₂ < ν₂/ν₁` (Barahona & Pecora 2002) — topology on the
  left, dynamics on the right. Above that the remedy is a different
  network, not a different coupling strength.

**Still open.**
- The MSF window `(ν₁, ν₂)` must be measured from the node dynamics. The
  module takes it as an input and cannot check it.
- `1/φ²` in the placeholder is still aesthetic. The scalar-input case has
  no derived answer.
- The core `CoherenceMetric` default is *unchanged* — `C* = I/φ` is still
  what you get if you construct one without arguments. Changing it would
  silently move every existing reading, so the defect is documented
  rather than patched. **Anyone using the default is using the falsified
  form.**

---

## F-3 · A single M(S) number is a reading

**[FALSIFIED]** · claimed 2025-11-27 (`a154de4`) · revised 2026-08-13 (`40b99be`)

**Claim.** M(S) returns one number, and that number is the measurement.

**Run.** Propagate plausible input ranges through the formula instead of
midpoints:

```
R_e ∈ [0.60, 0.90]   A ∈ [0.50, 0.90]   D ∈ [0.50, 0.90]
f(C) ∈ [0.75, 0.95]  L ∈ [0.15, 0.35]
```

**Result.** The midpoints give `M(S) = +0.06` — **GREEN**. The propagated
interval is `[−0.2375, +0.5426]`, width 0.78, and the same evidence is
consistent with **RED**. The gain term is a *product*, so relative
uncertainties compound rather than average out. The point estimate was
false precision, and the signal read off it was an artifact of the point
chosen.

**Revised claim.** `src/measurement/uncertainty.py`. Interval arithmetic
gives **tight and guaranteed** bounds — M(S) is monotone increasing in
R_e/A/D/f(C) and decreasing in L, so the extremes sit at opposite corners
of the input box (pinned by a test that no interior sample escapes and
both extremes are attained). The headline output is `verdict_determined`,
evaluated at **all 32 corners** rather than only the M(S) extremes,
because BLACK is triggered by a structural term reaching zero, which need
not coincide with an M(S) extreme.

**Still open.**
- `monte_carlo` assumes **independence between inputs**, and that is the
  assumption most likely to be wrong: the stress that drains `R_e`
  usually erodes `A` and `D` too. Correlated propagation is not
  implemented. The output states the assumption; it cannot repair it.
- It also assumes a distribution shape, which is stated and unvalidated.
- Nothing forces a caller to use this. `calculate_from_state` still
  returns a bare float.

---

## F-4 · Zero flux means dead

**[FALSIFIED]** · claimed 2026-04-20 (`4e133cc`) · revised 2026-08-13 (`00e6b40`)

**Claim.** The gain term is multiplicative, so any of `R_e`, `A`, `D`
reaching zero takes the product to zero. The verdict layer reports that as
**BLACK — irreversible from within**.

**Run.** Check the claim against systems known to read zero and recover.

**Result.** Falsified by cryptobiosis. Anhydrobiotic tardigrades suspend
metabolism and resume. Judean date palm seeds have germinated after ~2000
years. A dormant system reads `R_e = A = D = 0` exactly like a dead one,
so BLACK is a **false positive on anything folded**. And no repair to the
flux measurement can fix it: **during dormancy there is no flux to
measure.** The measurement channel itself was wrong, not its threshold.

**Revised claim.** `src/measurement/dormancy.py` measures the *seed*
instead of the flux. `fold` compresses the structural terms to
proportions plus a conserved total — the seed *is* the structure at
minimum energy, so it is scale-free and can re-expand at whatever scale
the future allows; `metric_signature` carries the measurement context
back so re-expansion is faithful in shape, not only in amplitude.

Three quantitative constraints stop this from being wishful:

- **Folding costs energy**, so `fold_window` closes while the system is
  still alive — the option expires before the system does.
- **Preservation decays on a clock**: the Ellis & Roberts viability
  equation (1980, *Annals of Botany* 45:13),
  `log σ = K_E − C_W log m − C_H t − C_Q t²`, with σ spanning 56,000 down
  to 96 periods across the stress range.
- **Over-compression destroys the seed**: residual activity below the ~2%
  floor is charged against initial viability rather than rewarded with
  longevity.

`assess_dormancy(None)` returns `NEVER_FOLDED` and states that a missing
seed is **absent evidence, not proof of death**.

**Still open.**
- The default viability constants are measured for **orthodox seeds**.
  Applying them to an institution, a community or a codebase is an
  analogy. Every reading says so; nothing prevents it.
- The framework still cannot distinguish dormancy from death for a system
  that never folded. `NEVER_FOLDED` is honest about this and does not
  resolve it.
- No empirical case has been run through `fold` → long gap → re-expansion
  end to end. The clock is cited, not reproduced here.

---

## F-5 · Four standalone audits each measure something real

**[FALSIFIED]** · claimed 2026-04-25 → 2026-05-01 · revised 2026-08-13 (`a33657b`, `06d01ee`)

**Claim.** The business, dependency, premise and substrate audits each
measure something real about a system.

**Run.** Trace what any of them contributes to M(S).

**Result.** Nothing. Each produced its own verdict in its own units and
**M(S) never saw any of them.** Four opinions sitting beside a
measurement is not the same as a measurement. The individual claim was
true and the aggregate claim — that the repository measured coherence —
was not.

**Revised claim.** `src/measurement/audit_bridge.py`. `from_business_audit`,
`from_dependency_graph`, `from_substrate_audit` and `from_premise_audit`
each return a `BridgedSystem` (state + metric + calibrations + notes),
where **every term assignment states its assumption in the output**. The
dependency bridge imports the audit's own `cascade_disruption` by
reference rather than reimplementing it, so the bridge cannot drift from
the propagation logic it claims to bridge.

**Still open.**
- There is no objectively correct way to say "workforce health *is*
  `R_e`". The mappings are arguable by construction — that is why each is
  a sentence you can disagree with rather than a constant you cannot see.
- `legacy/premise_audit/validity_weighted_reweighting.py` still has **no
  bridge**. The gap the entry above describes is still open for that one
  module.

---

## F-6 · Citation weight normalized by per-study maximum

**[FALSIFIED]** · claimed 2026-05-01 (`a5da241`) · revised 2026-05-01 (`0698059`)

The tightest loop in the repository — hypothesis to falsification to
revision inside one day. Kept because it shows the loop at a scale small
enough to see all of at once.

**Claim.** `raw_citation_weight` normalizes a claim's summed citation
count by the largest per-study citation count in the corpus, yielding a
value in [0, 1] comparable to `validity_weight`.

**Run.** The module's own demo.

**Result.** Claim C2 read **1.625**. When several studies assert the same
claim, the sum exceeds any individual study's count, so the value escapes
[0, 1] and stops matching the scale of `validity_weight` — which the
divergence report compares against directly. The divergence numbers were
wrong wherever a claim had multiple sources, which is the normal case.

**Revised claim.** Normalize by the **largest claim-total** in the corpus
(`_claim_citation_total`), keeping the result in [0, 1] and on
`validity_weight`'s scale.

**Still open.**
- Neither `raw_citation_weight` nor `validity_weight` has test coverage.
  This was caught by reading demo output, which is not a test, and the
  same class of error would not be caught again.

---

## F-7 · The audit packages are importable from the repository root

**[FALSIFIED]** · claimed 2026-05-01 (`a5da241`) · revised 2026-08-14

**Claim.** The audit packages resolve as namespace packages from the
repository root — as stated in `CLAUDE.md`.

**Run.** `python -c "import premise_audit.validity_weighted_reweighting"`
from the root.

**Result.** `ModuleNotFoundError: No module named
'premise_cross_domain_audit'`. The module used a **flat** import of its
sibling, so it ran only when executed from inside its own directory. It
had been broken from the root since the day it landed, and **no test
covered it**, so nothing said so for three months. Every other module in
the repository is imported by a test; this one was not.

**Revised claim.** Package-relative import with a fallback for loose
script execution, and `tests/test_legacy_imports.py` pins that every
module under `legacy/` imports from the root and keeps a demo entry
point.

**Still open.**
- The new test pins *importability*, not behaviour.
  `validity_weighted_reweighting` still has no behavioural coverage —
  see F-6.

---

## F-8 · The documented command runs the worked example

**[FALSIFIED]** · claimed 2026-08-13 (`082390d`) · revised 2026-08-14

**Claim.** `README.md` instructs the reader to run the community example
with `python examples/run_community_year.py`.

**Run.** That exact command, from the repository root.

**Result.** `ModuleNotFoundError: No module named 'src'`. Running a file
by path puts `examples/` on `sys.path`, not the repository root, so the
script's own imports fail. The example's own docstring had carried the
correct form (`python -m examples.run_community_year`) since it was
written on 2026-04-20 (`d269d36`); the README contradicted it. The commit
that introduced the wrong command was titled *"Fix phantom README
references"* — it removed some and added one, because **nothing runs the
README.**

Found the same day as F-7 and by the same method: executing the
documented commands instead of reading them. Two published entry points
did not work, and neither failure was visible from reading.

**Revised claim.** `README.md` now gives the `-m` form and says why.

**Still open.**
- Nothing tests that documented commands run. The test suite covers the
  library; the README is unexecuted prose, and this class of defect
  will recur silently.
- The general lesson generalizes past this repository: **an instruction
  nobody executes is an untested claim**, and it decays exactly like an
  uncalibrated constant.

---

# Rejected alternatives

Approaches that were tested and did not survive the test, so they never
shipped. Recorded because the reasoning is not visible in the code that
replaced them, and the next person will otherwise reach for the same
thing.

## R-1 · A bare Kendall tau threshold detects a rising indicator

**Considered for** `src/measurement/early_warning.py`

**Claim.** Critical slowing down shows up as rising lag-1 autocorrelation
and rising variance, so flag it when the Kendall tau of the rolling
indicator reaches the literature convention `|τ| ≥ 0.5`.

**Run.** 60 stationary AR(1) series (α = 0.2, seeded) that are approaching
nothing, scored both ways. Reproduce with:

```python
from tests.test_early_warning import ar1_series
from src.measurement.early_warning import critical_slowing_down

critical_slowing_down(ar1_series(0.2, seed=s), significance=False)  # bare threshold
critical_slowing_down(ar1_series(0.2, seed=s))                      # surrogate-tested
```

**Result.**

| | any flag | joint flag |
|---|---|---|
| bare `\|τ\| ≥ 0.5` | **45%** | 8% |
| surrogate-tested | **5%** | 0% |

A bare threshold fires on nearly half of series that are doing nothing.
The reason is structural, not a bad threshold choice: **rolling windows
overlap**, so the indicator series is itself strongly autocorrelated and
large |τ| arises by chance. Raising the threshold trades the false alarms
for missed detections; it does not fix the cause.

**Adopted instead.** Observed τ is compared against a null distribution
built from surrogate series with the same fitted AR(1) structure and no
trend in recovery rate (Dakos et al. 2012, *PLoS ONE* 7:e41010). 100
surrogates, p ≤ 0.05, generator seeded explicitly so a reading is
reproducible from its inputs. Measured operating characteristics on the
module's own 12-seed benchmark: **~75% detection on eroding series, ~8%
false alarm on stationary**, pinned in `tests/test_early_warning.py`.

**Still open.**
- The benchmark is synthetic AR(1) with a known answer. The ~67.8%
  real-world detection rate (Dakos et al. 2024, *Nature Ecology &
  Evolution*) is cited, not reproduced here.
- **No signal is not evidence of safety.** Roughly a third of real
  transitions give no advance warning, and interdependent networks
  jumping discontinuously (Buldyrev et al. 2010) give none by
  construction. The module carries this in its output; it cannot detect
  what it says it cannot detect.
- 100 surrogates was chosen as the smallest count reproducing the same
  flags as 200 on one demo series. That is a convenience calibration on a
  single series, not a power analysis.

## R-2 · Read a dependency graph's declared attributes as its coherence

**Considered for** `audit_bridge.from_dependency_graph`

**Claim.** The graph already carries import fractions, replacement times
and SPOF flags. Aggregate them into D.

**Result.** Declared attributes describe what someone believed about the
graph, not how it behaves. Worse, a single 100%-loss probe cannot
distinguish a component that degrades gracefully from one that fails at
the first nudge — and under min-bottleneck propagation, `D = 0` comes out
as an **artifact of the propagation rule** rather than a property of the
system.

**Adopted instead.** Probe each node across `STRESS_GRADIENT =
(0, 0.25, 0.5, 0.75, 1.0)` and record the target's surviving throughput.
**The response curves are the measurement.** The bridge explicitly flags
when zero diversity is a min-bottleneck artifact rather than a finding.

**Still open.** The gradient is five arbitrary levels. Nothing establishes
that five is enough or that even spacing is right.

## R-3 · Substrate-audit diversity is average layer health

**Considered for** `audit_bridge.from_substrate_audit`

**Claim.** The substrate audit has four layers with health scores. Average
them into D.

**Result.** An evenness measure reads **four half-capacity layers as
maximum diversity**, which inverts what D is for — D counts viable
strategies, and four half-broken routes are not four routes. It also
double-counts: average health is already what `R_e` is measuring.

**Adopted instead.** D scores **viable routes** from the three-band layer
verdicts (`DEMONSTRABLE` 1.0 / `PARTIAL` 0.5 / `OPAQUE` 0.0). An OPAQUE
layer is not a route. Separately, the audit's own cascade rule maps onto
A: substrate denial blocks correction ⇒ `A = 0` ⇒ BLACK.

**Still open.** The 1.0 / 0.5 / 0.0 band weights are a choice, not a
measurement. `PARTIAL = 0.5` in particular is a midpoint with nothing
behind it.

---

# Never tested

Claims the framework currently makes that **nothing has been run
against**. Listed so that they are not mistaken for the entries above,
which were.

- **`golden_ratio_trust`** — that trust emerges in φ-ratio chambers and
  stages cannot be skipped. Tests pin that the implementation follows the
  φ ratio; nothing tests that trust does.
- **`empathy_types`** — that tribal empathy scores negative coherence and
  AI swarm reciprocity scores maximum. The tests pin the ordering the
  module asserts, which is the module agreeing with itself.
- **`replacement_analysis`** — the verdict thresholds separating
  THERMODYNAMICALLY_SUPERIOR from THERMODYNAMICALLY_STUPID are
  unvalidated cut points.
- **The φ placeholder wherever it appears in a coupling optimum** — see
  F-2. Aesthetic, and labelled as such in its own docstring.
- **The GREEN/AMBER/RED band edges** in `coherence_verdict` — no
  calibration against observed collapses.
- **Linear time-to-collapse projection** in `coherence_verdict` — a linear
  extrapolation of a metric whose whole premise is that systems approach
  transitions *non*-linearly. The one place the framework contradicts its
  own physics.

---

## Adding an entry

When a run changes a claim, add the entry before or with the fix, not
after. The template:

```markdown
## F-n · <the claim, in its own words>

**[FALSIFIED|REJECTED]** · claimed <date> (`<sha>`) · revised <date> (`<sha>`)

**Claim.**    What was asserted, stated so it could be wrong.
**Run.**      What was actually done. Reproducible, with the command.
**Result.**   What was observed. Numbers, not adjectives.
**Revised claim.**  What stands now, and where it lives.
**Still open.**     What the revision did not close.
```

Rules the log lives by:

1. **Do not delete the old claim.** Its date still carries — see
   [`legacy/README.md`](../legacy/README.md).
2. **Numbers, not adjectives.** "Fires too often" is not a result. "45%
   of 60 stationary series" is.
3. **Never leave `Still open` empty.** A revision that closed everything
   has not been looked at hard enough yet.
4. **A revision is not a validation.** Surviving one test is not the same
   as being right, and everything under *Never tested* stays there until
   something is actually run.
