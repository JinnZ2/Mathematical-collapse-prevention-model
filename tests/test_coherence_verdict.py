"""Falsifiable tests for src.measurement.coherence_verdict."""

import unittest

import numpy as np

from src.core.coherence_metric import PHI, SystemState
from src.measurement.coherence_verdict import (
    assess,
    time_to_collapse,
    trajectory_from_history,
    yield_signal,
)


def _healthy_state():
    return SystemState(
        resonance_energy=0.9,
        adaptability=0.85,
        diversity=0.8,
        coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
        loss_rate=0.1,
        energy_cost=6,
        description="healthy",
    )


class TrajectoryTests(unittest.TestCase):
    def test_single_point_is_stable(self):
        self.assertEqual(trajectory_from_history([0.5]), "STABLE")

    def test_improving(self):
        self.assertEqual(trajectory_from_history([0.1, 0.2, 0.3]), "IMPROVING")

    def test_degrading(self):
        self.assertEqual(trajectory_from_history([0.3, 0.2, 0.1]), "DEGRADING")

    def test_flat_is_stable(self):
        self.assertEqual(trajectory_from_history([0.2, 0.2, 0.2]), "STABLE")


class TimeToCollapseTests(unittest.TestCase):
    def test_linear_projection(self):
        # step = -0.25, current = 0.25 -> 1.0 period until zero
        self.assertAlmostEqual(time_to_collapse([1.0, 0.75, 0.5, 0.25]), 1.0)

    def test_none_when_improving(self):
        self.assertIsNone(time_to_collapse([0.1, 0.2, 0.3]))

    def test_zero_when_already_nonpositive(self):
        self.assertEqual(time_to_collapse([0.2, 0.0]), 0.0)

    def test_none_when_insufficient_history(self):
        self.assertIsNone(time_to_collapse([0.5]))


class YieldSignalTests(unittest.TestCase):
    def test_irreversibility_forces_black(self):
        self.assertEqual(yield_signal(0.9, ["diversity"], None, "STABLE"), "BLACK")

    def test_negative_m_is_red(self):
        self.assertEqual(yield_signal(-0.1, [], None, "STABLE"), "RED")

    def test_imminent_collapse_is_red(self):
        self.assertEqual(yield_signal(0.4, [], 0.5, "DEGRADING"), "RED")

    def test_near_cliff_is_amber(self):
        self.assertEqual(yield_signal(0.4, [], 3.0, "DEGRADING"), "AMBER")

    def test_healthy_is_green(self):
        self.assertEqual(yield_signal(0.9, [], None, "STABLE"), "GREEN")


class AssessTests(unittest.TestCase):
    def test_healthy_green(self):
        v = assess(_healthy_state())
        self.assertEqual(v.signal, "GREEN")
        self.assertEqual(v.irreversible_components, [])

    def test_zero_diversity_black(self):
        state = SystemState(
            resonance_energy=0.5,
            adaptability=0.5,
            diversity=0.0,
            coupling_matrix=np.eye(2) / PHI,
            loss_rate=0.1,
            description="monoculture",
        )
        v = assess(state)
        self.assertEqual(v.signal, "BLACK")
        self.assertIn("diversity", v.irreversible_components)

    def test_degrading_history_triggers_warning(self):
        # current M(S) is still positive but shrinking
        state = SystemState(
            resonance_energy=0.5,
            adaptability=0.5,
            diversity=0.5,
            coupling_matrix=np.array([[1 / PHI, 0.3], [0.3, 1 / PHI]]),
            loss_rate=0.1,
            description="eroding",
        )
        v = assess(state, history=[0.40, 0.32, 0.24, 0.17])
        self.assertEqual(v.trajectory, "DEGRADING")
        # either ttc warning or degrading-trajectory warning should fire
        self.assertTrue(any("collapse" in w or "degrading" in w for w in v.warnings))


if __name__ == "__main__":
    unittest.main()
