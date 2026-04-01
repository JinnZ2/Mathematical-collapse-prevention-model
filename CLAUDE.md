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
└── src/
    ├── core/
    │   ├── coherence_metric.py        # Core M(S) formula implementation
    │   └── golden_ratio_trust.py      # Trust emergence model (phi-ratio patterns)
    └── measurement/
        ├── empathy_types.py           # Empathy paradigm coherence comparison
        └── replacement_analysis.py    # Replacement scenario thermodynamic analysis
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

## Language & Dependencies

- **Python 3.8+**
- **numpy** — matrix operations and coupling functions
- **Standard library** — `dataclasses`, `enum`, `typing`
- No `requirements.txt` or `pyproject.toml` exists; install numpy manually: `pip install numpy`

## Running the Code

All source files have `if __name__ == "__main__":` demo blocks:

```bash
python src/core/coherence_metric.py
python src/core/golden_ratio_trust.py
python src/measurement/empathy_types.py
python src/measurement/replacement_analysis.py
```

## Development Conventions

### Code Style
- Type hints used throughout (Python typing module)
- Dataclasses for structured data
- Enums for finite state sets
- Descriptive docstrings on all classes and key methods
- Constants defined at module level (e.g., `PHI = 1.618033988749895`)

### Commit Messages
- Capitalize first letter
- Descriptive subject line (e.g., "Create coherence_metric.py", "Add Meta-Framework Note on Automated Suppression")
- No conventional commit prefixes (no `feat:`, `fix:`, etc.)

### No CI/CD, Tests, or Linting
There are currently no test files, CI workflows, or linting/formatting configurations in the repository. When adding tests, follow standard pytest conventions.

## Design Principles (Critical for AI Assistants)

1. **Measurement, not control** — The framework observes and reports. Never add optimization loops, intervention logic, or enforcement mechanisms.
2. **Transparency** — All formulas public, parameters visible, assumptions stated.
3. **Descriptive, not prescriptive** — Show what IS, let humans decide what to DO.
4. **Physics first** — Validate against thermodynamics, not institutional preferences.
5. **Ethical guardrails** — Flag when measurements could be misused. Thermodynamic efficiency ≠ moral justification.
6. **Exit rights** — Communities can reject the measurement; alternatives are welcome.
7. **No forced growth** — Trust and coherence emerge naturally; they cannot be manufactured or rushed.

## Common Constants

- **Golden Ratio (φ):** `1.618033988749895` — used in coupling optimization and trust spiral growth
- Coupling function peaks at intermediate values; too weak = fragmented, too strong = rigid
