# legacy/

Work that came first.

Nothing here is retired, broken, or deprecated. This folder is a
**precedence record**: it holds the standalone tools and origin documents
that predate the `src/` framework, in the order they appeared, with what
now carries their work named alongside them.

The distinction matters because these are two different facts:

- *This code was superseded* — it no longer runs, and something else does
  the job. **Not true of anything here.**
- *This code came first, and something later was built on top of it* —
  the original still runs, and the date of its first claim still stands.
  **That is what this folder records.**

Every module below is still imported, still exercised by the test suite,
and still runnable on its own. Moving them under `legacy/` says when they
arrived, not that they stopped mattering.

## Contents

| Path | First appeared | Carried forward by |
|---|---|---|
| `Meta-Framework-Note.md` | 2025-11-29 (`fcc92b9`) | `docs/TRUTH_TELLING.md` |
| `dependency_audit/refinery_dependency_graph.py` | 2026-04-25 (`2822c91`) | `audit_bridge.from_dependency_graph` |
| `business_audit/business_resilience_framework.py` | 2026-04-26 (`2f389c2`) | `audit_bridge.from_business_audit` |
| `premise_audit/premise_cross_domain_audit.py` | 2026-05-01 (`0551d67`) | `audit_bridge.from_premise_audit` |
| `substrate_audit/substrate_aware_audit.py` | 2026-05-01 (`0551d67`) | `audit_bridge.from_substrate_audit` |
| `premise_audit/validity_weighted_reweighting.py` | 2026-05-01 (`a5da241`) | — (no bridge yet) |

`validity_weighted_reweighting` is the one entry with no bridge into
M(S). It reweights claims by premise validity rather than citation count,
and nothing in `src/measurement` reads it. That is an opening, not a
defect.

### Licensing

`business_resilience_framework.py`, `refinery_dependency_graph.py` and
`substrate_aware_audit.py` carry **CC0** headers from before the
repository settled on MIT. The headers are left as written — they are
part of the record of what was released, and when. The repository
`LICENSE` (MIT) governs the rest.

## Using them

They are importable from the repository root as ordinary namespace
packages:

```python
from legacy.business_audit.business_resilience_framework import full_audit
from legacy.dependency_audit.refinery_dependency_graph import build_us_refinery_graph
from legacy.premise_audit.premise_cross_domain_audit import build_example_engine
from legacy.substrate_audit.substrate_aware_audit import reference_audit_honest_llm
```

Each has a runnable demo:

```bash
python -m legacy.business_audit.business_resilience_framework
python -m legacy.dependency_audit.refinery_dependency_graph
python -m legacy.premise_audit.premise_cross_domain_audit
python -m legacy.premise_audit.validity_weighted_reweighting
python -m legacy.substrate_audit.substrate_aware_audit
```

Run from the repository root. `tests/test_legacy_imports.py` pins that
every module here imports from the root and that its demo entry point
still exists — so the folder cannot quietly rot into an archive that no
longer runs.

## Why not delete any of it

The framework's method is to state a claim, run it, and record what the
run did to the claim (see
[`docs/FALSIFICATION_LOG.md`](../docs/FALSIFICATION_LOG.md)). Deleting a
superseded claim erases the evidence that the revision was earned. A
reader who only sees the current version cannot tell which parts were
derived, which were corrected under pressure, and which have never been
tested at all.

So: superseded code moves here and the log records why. It does not get
removed.
