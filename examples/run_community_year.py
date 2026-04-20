"""
Worked example: a small rural community tracked over twelve months.

Reads community_year.csv, computes M(S) and a GREEN/AMBER/RED/BLACK
verdict for each month, and shows how the signal shifts as diversity
erodes and loss accumulates.

Run from the repo root:
    python -m examples.run_community_year
"""

from __future__ import annotations

import csv
import os
from typing import List

import numpy as np

from src.core.coherence_metric import PHI, CoherenceMetric, SystemState
from src.measurement.coherence_verdict import assess


CSV_PATH = os.path.join(os.path.dirname(__file__), "community_year.csv")

# Fixed coupling for the whole year. In a real study this would also
# evolve; kept constant here to isolate the effect of the other inputs.
COUPLING = np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]])


def _row_to_state(row: dict) -> SystemState:
    return SystemState(
        resonance_energy=float(row["resonance_energy"]),
        adaptability=float(row["adaptability"]),
        diversity=float(row["diversity"]),
        coupling_matrix=COUPLING,
        loss_rate=float(row["loss_rate"]),
        description=row["note"],
    )


def main() -> None:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    metric = CoherenceMetric()
    history: List[float] = []

    print("=" * 78)
    print(f"{'month':<9}{'M(S)':>10}{'signal':>10}{'trajectory':>14}   note")
    print("=" * 78)

    for row in rows:
        state = _row_to_state(row)
        verdict = assess(state, history=history, metric=metric)
        history.append(verdict.coherence)

        print(
            f"{row['month']:<9}"
            f"{verdict.coherence:>+10.3f}"
            f"{verdict.signal:>10}"
            f"{verdict.trajectory:>14}   {row['note']}"
        )

    print("=" * 78)
    print(
        "The framework reports what is. It does not say what to do about it.\n"
        "Residents decide whether these readings warrant action, and which."
    )


if __name__ == "__main__":
    main()
