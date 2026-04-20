"""Falsifiable tests for src.core.coherence_metric."""

import math
import unittest

import numpy as np

from src.core.coherence_metric import PHI, CoherenceMetric, SystemState


class CouplingFunctionTests(unittest.TestCase):
    def test_peaks_at_optimum(self):
        metric = CoherenceMetric()
        n = 2
        optimum = np.eye(n) / PHI
        self.assertAlmostEqual(metric.coupling_function(optimum), 1.0, places=9)

    def test_decays_away_from_optimum(self):
        metric = CoherenceMetric(alpha=1.0)
        optimum = np.eye(2) / PHI
        far = np.array([[5.0, 0.0], [0.0, 5.0]])
        self.assertLess(metric.coupling_function(far), 0.01)

    def test_monotonic_decay_with_distance(self):
        metric = CoherenceMetric(alpha=1.0)
        near = np.eye(2) / PHI + 0.1
        far = np.eye(2) / PHI + 0.5
        self.assertGreater(
            metric.coupling_function(near),
            metric.coupling_function(far),
        )


class CoherenceCalculationTests(unittest.TestCase):
    def test_healthy_system_is_positive(self):
        metric = CoherenceMetric()
        m = metric.calculate(
            resonance_energy=0.9,
            adaptability=0.85,
            diversity=0.8,
            coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
            loss_rate=0.1,
        )
        self.assertGreater(m, 0.0)

    def test_high_loss_makes_m_negative(self):
        metric = CoherenceMetric()
        m = metric.calculate(
            resonance_energy=0.3,
            adaptability=0.4,
            diversity=0.2,
            coupling_matrix=np.array([[2.0, 0.1], [0.1, 2.0]]),
            loss_rate=0.8,
        )
        self.assertLess(m, 0.0)

    def test_zero_diversity_kills_gain(self):
        metric = CoherenceMetric()
        m = metric.calculate(
            resonance_energy=1.0,
            adaptability=1.0,
            diversity=0.0,
            coupling_matrix=np.eye(2) / PHI,
            loss_rate=0.0,
        )
        self.assertEqual(m, 0.0)


class EfficiencyTests(unittest.TestCase):
    def test_efficiency_ratio_returns_none_without_cost(self):
        state = SystemState(
            resonance_energy=0.8,
            adaptability=0.8,
            diversity=0.8,
            coupling_matrix=np.eye(2) / PHI,
            loss_rate=0.1,
        )
        self.assertIsNone(CoherenceMetric().efficiency_ratio(state))

    def test_efficiency_ratio_scales_inversely_with_cost(self):
        metric = CoherenceMetric()
        cheap = SystemState(0.9, 0.9, 0.9, np.eye(2) / PHI, 0.1, energy_cost=10)
        expensive = SystemState(0.9, 0.9, 0.9, np.eye(2) / PHI, 0.1, energy_cost=100)
        self.assertGreater(
            metric.efficiency_ratio(cheap),
            metric.efficiency_ratio(expensive),
        )


class CompareSystemsTests(unittest.TestCase):
    def test_never_decides_replacement(self):
        metric = CoherenceMetric()
        a = SystemState(0.9, 0.9, 0.9, np.eye(2) / PHI, 0.1, energy_cost=6)
        b = SystemState(0.3, 0.3, 0.3, np.eye(2) / PHI, 0.8, energy_cost=1000)
        result = metric.compare_systems(a, b)
        # Core promise: measurement returns info, not a decision.
        self.assertIsNone(result["replacement_makes_sense"])
        self.assertIn("MEASUREMENT, not prescription", result["interpretation"])


if __name__ == "__main__":
    unittest.main()
