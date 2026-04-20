"""Falsifiable tests for src.measurement.sensitivity."""

import unittest

import numpy as np

from src.core.coherence_metric import PHI, SystemState
from src.measurement.sensitivity import PARAMETERS, sensitivity


def _healthy_state():
    return SystemState(
        resonance_energy=0.9,
        adaptability=0.85,
        diversity=0.8,
        coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
        loss_rate=0.1,
        energy_cost=6,
    )


class SlopeSignTests(unittest.TestCase):
    def test_loss_rate_slope_is_minus_one(self):
        # L enters the formula as a direct subtraction, so ∂M/∂L = -1 exactly
        r = sensitivity(_healthy_state())
        self.assertAlmostEqual(r.normalized["loss_rate"], -1.0, places=6)

    def test_gain_parameters_are_positive(self):
        r = sensitivity(_healthy_state())
        for name in ("resonance_energy", "adaptability", "diversity"):
            self.assertGreater(r.normalized[name], 0.0, f"{name} should raise M(S)")


class CouplingOptimumTests(unittest.TestCase):
    def test_slope_is_zero_at_phi_optimum(self):
        # At the peak of f(C), first derivative vanishes — a fixed point
        # of the coupling function; useful sanity check on the whole pipeline
        state = SystemState(
            resonance_energy=0.9,
            adaptability=0.85,
            diversity=0.8,
            coupling_matrix=np.eye(2) / PHI,  # exactly at the optimum
            loss_rate=0.1,
        )
        r = sensitivity(state)
        self.assertAlmostEqual(r.normalized["coupling_matrix"], 0.0, places=4)


class DegenerateStateTests(unittest.TestCase):
    def test_zero_diversity_flattens_gain_parameters(self):
        # If D=0, the gain term is 0 regardless of R_e, A, f(C); so small
        # bumps to those three should barely move M(S) at all
        state = SystemState(
            resonance_energy=0.9,
            adaptability=0.85,
            diversity=0.0,
            coupling_matrix=np.eye(2) / PHI,
            loss_rate=0.1,
        )
        r = sensitivity(state)
        for name in ("resonance_energy", "adaptability"):
            self.assertLess(
                abs(r.normalized[name]),
                1e-6,
                f"{name} should have near-zero slope when diversity=0",
            )


class RankingTests(unittest.TestCase):
    def test_ranking_covers_all_parameters(self):
        r = sensitivity(_healthy_state())
        self.assertEqual(set(name for name, _ in r.ranking), set(PARAMETERS))

    def test_ranking_is_sorted_by_abs_slope(self):
        r = sensitivity(_healthy_state())
        slopes = [abs(s) for _, s in r.ranking]
        self.assertEqual(slopes, sorted(slopes, reverse=True))


class ReproducibilityTests(unittest.TestCase):
    def test_baseline_state_is_not_mutated(self):
        state = _healthy_state()
        C_before = state.coupling_matrix.copy()
        R_before = state.resonance_energy
        sensitivity(state)
        self.assertTrue(np.array_equal(state.coupling_matrix, C_before))
        self.assertEqual(state.resonance_energy, R_before)


if __name__ == "__main__":
    unittest.main()
