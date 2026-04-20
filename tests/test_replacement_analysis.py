"""Falsifiable tests for src.measurement.replacement_analysis."""

import unittest

import numpy as np

from src.core.coherence_metric import PHI, SystemState
from src.measurement.replacement_analysis import (
    ReplacementAnalysis,
    ReplacementScenario,
)


def _worker():
    return SystemState(
        resonance_energy=0.9,
        adaptability=0.85,
        diversity=0.8,
        coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
        loss_rate=0.1,
        energy_cost=6,
        description="Efficient rural human worker",
    )


def _robot():
    return SystemState(
        resonance_energy=0.4,
        adaptability=0.3,
        diversity=0.2,
        coupling_matrix=np.array([[1.5, 0.1], [0.1, 1.5]]),
        loss_rate=0.2,
        energy_cost=60,
        description="Industrial robot",
    )


class VerdictTests(unittest.TestCase):
    def test_worse_on_both_axes_is_stupid(self):
        scenario = ReplacementScenario(
            current=_worker(),
            replacement=_robot(),
            context="human to robot",
            ethical_considerations="consent discussed",
        )
        result = ReplacementAnalysis().analyze(scenario)
        self.assertIn("STUPID", result["thermodynamic_verdict"])

    def test_better_on_both_axes_is_superior(self):
        # wasteful baseline, efficient replacement
        wasteful = SystemState(
            resonance_energy=0.3, adaptability=0.4, diversity=0.2,
            coupling_matrix=np.array([[2.0, 0.1], [0.1, 2.0]]),
            loss_rate=0.8, energy_cost=1000,
            description="wasteful extraction system",
        )
        efficient = SystemState(
            resonance_energy=0.85, adaptability=0.9, diversity=0.75,
            coupling_matrix=np.array([[1 / PHI, 0.5], [0.5, 1 / PHI]]),
            loss_rate=0.1, energy_cost=100,
            description="efficient alternative",
        )
        scenario = ReplacementScenario(
            current=wasteful,
            replacement=efficient,
            context="wasteful to efficient",
            ethical_considerations="with consent",
        )
        result = ReplacementAnalysis().analyze(scenario)
        self.assertIn("SUPERIOR", result["thermodynamic_verdict"])


class EthicalFlagTests(unittest.TestCase):
    def test_human_replacement_is_critical(self):
        scenario = ReplacementScenario(
            current=_worker(),
            replacement=_robot(),
            context="human to robot",
            ethical_considerations="no consent",
        )
        result = ReplacementAnalysis().analyze(scenario)
        severities = {f["flag"]: f["severity"] for f in result["ethical_flags"]}
        self.assertEqual(severities.get("HUMAN_REPLACEMENT"), "CRITICAL")

    def test_missing_consent_mentions_flag(self):
        scenario = ReplacementScenario(
            current=_worker(),
            replacement=_robot(),
            context="human to robot",
            ethical_considerations=None,
        )
        result = ReplacementAnalysis().analyze(scenario)
        flags = {f["flag"] for f in result["ethical_flags"]}
        self.assertIn("NO_CONSENT", flags)


if __name__ == "__main__":
    unittest.main()
