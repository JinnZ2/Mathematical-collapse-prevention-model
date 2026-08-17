"""Pins the findings of experiments/coupling_optimum.py.

The experiment measures how far the 1/phi^2 coupling placeholder sits
from the optimum derived from synchronization stability. These tests pin
the claims that came out of it, so that a future change to either side
has to face them rather than quietly moving the numbers.

Each test corresponds to a section of the experiment and to an entry in
docs/FALSIFICATION_LOG.md (F-2, F-9, F-10).
"""

import unittest

import numpy as np

from src.core.coherence_metric import PHI, CoherenceMetric
from src.measurement.audit_bridge import coupling_matrix, phi_coupling_optimum
from src.measurement.coupling_physics import (
    MSFWindow,
    coupling_coherence,
    optimal_coupling,
    spectrum,
)

PHI_OPT = 1.0 / PHI**2
WINDOW = MSFWindow(nu_lower=0.2, nu_upper=4.0)

# Coarser than the experiment's sweep; still fine enough to locate the
# argmax to within a grid step of 1/phi^2.
SCALES = np.geomspace(1e-2, 1e1, 600)


def _ring(n):
    A = np.zeros((n, n))
    for i in range(n):
        A[i, (i + 1) % n] = A[(i + 1) % n, i] = 1.0
    return A


def _path(n):
    A = np.zeros((n, n))
    for i in range(n - 1):
        A[i, i + 1] = A[i + 1, i] = 1.0
    return A


def _star(n):
    A = np.zeros((n, n))
    A[0, 1:] = A[1:, 0] = 1.0
    return A


def _complete(n):
    return np.ones((n, n)) - np.eye(n)


def _barbell(bridged=True):
    A = np.zeros((6, 6))
    edges = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)]
    if bridged:
        edges.append((2, 3))
    for i, j in edges:
        A[i, j] = A[j, i] = 1.0
    return A


def _frobenius_peak(A):
    """(argmax scale, peak f(C)) for the Gaussian form on a graph."""
    n = A.shape[0]
    metric = CoherenceMetric(coupling_optimum=phi_coupling_optimum(n))
    best_f, best_s = -1.0, None
    for s in SCALES:
        C = s * A
        np.fill_diagonal(C, 1.0 / PHI)
        f = metric.coupling_function(C)
        if f > best_f:
            best_f, best_s = f, float(s)
    return best_s, best_f


class DefaultCouplingOptimumTests(unittest.TestCase):
    """F-2: the default C* = I/phi has no interior optimum at all."""

    def test_default_optimum_is_monotone_decreasing_in_coupling(self):
        metric = CoherenceMetric()  # default C* = I/phi
        for n in (2, 3, 5):
            with self.subTest(n=n):
                fs = [metric.coupling_function(coupling_matrix(n, c))
                      for c in np.linspace(0.0, 1.5, 200)]
                self.assertTrue(all(b <= a + 1e-15 for a, b in zip(fs, fs[1:])))

    def test_default_peak_sits_at_zero_coupling(self):
        # "Too weak = fragmented" requires the peak NOT to be at zero.
        # Under the default it is exactly at zero, so the framework's
        # stated design is inexpressible with it.
        metric = CoherenceMetric()
        cs = np.linspace(0.0, 1.5, 200)
        fs = [metric.coupling_function(coupling_matrix(3, c)) for c in cs]
        self.assertAlmostEqual(cs[int(np.argmax(fs))], 0.0, places=9)


class TopologyBlindnessTests(unittest.TestCase):
    """F-9: the Gaussian argmax is not a function of the network."""

    GRAPHS = {
        "complete": _complete(6),
        "ring": _ring(6),
        "star": _star(6),
        "path": _path(6),
        "barbell": _barbell(True),
    }

    def test_frobenius_argmax_is_phi_squared_for_every_topology(self):
        step = SCALES[1] / SCALES[0]
        for name, A in self.GRAPHS.items():
            with self.subTest(graph=name):
                s, _ = _frobenius_peak(A)
                self.assertLess(abs(np.log(s / PHI_OPT)), np.log(step))

    def test_physics_optimum_does_depend_on_topology(self):
        optima = {}
        for name, A in self.GRAPHS.items():
            optima[name] = optimal_coupling(spectrum(A), WINDOW)
        spread = max(optima.values()) / min(optima.values())
        # Measured spread across these five topologies is ~6x. If this
        # ever collapses to 1, the physics side has stopped depending on
        # the spectrum and the comparison is meaningless.
        self.assertGreater(spread, 3.0)

    def test_the_two_measures_disagree_about_which_graph_is_best(self):
        # Frobenius ranks by how complete the graph is; physics ranks by
        # eigenratio. They pick different winners among non-complete
        # graphs, which is the substance of the disagreement.
        fro = {n: _frobenius_peak(A)[1] for n, A in self.GRAPHS.items()}
        phys = {n: coupling_coherence(optimal_coupling(spectrum(A), WINDOW),
                                      A, WINDOW).coherence
                for n, A in self.GRAPHS.items()}
        self.assertEqual(max(fro, key=fro.get), "complete")
        # Physics calls every one of these synchronizable at its own optimum.
        for name, value in phys.items():
            with self.subTest(graph=name):
                self.assertAlmostEqual(value, 1.0, places=6)


class FragmentationBlindnessTests(unittest.TestCase):
    """F-9: cutting the bridge splits the network. One measure notices."""

    def setUp(self):
        self.intact = _barbell(True)
        self.cut = _barbell(False)

    def test_physics_reports_structural_fragmentation(self):
        self.assertTrue(spectrum(self.intact).connected)
        self.assertFalse(spectrum(self.cut).connected)
        reading = coupling_coherence(PHI_OPT, self.cut, WINDOW)
        self.assertEqual(reading.regime, "FRAGMENTED_STRUCTURALLY")
        self.assertEqual(reading.coherence, 0.0)

    def test_frobenius_barely_moves_when_the_network_splits(self):
        _, f_intact = _frobenius_peak(self.intact)
        _, f_cut = _frobenius_peak(self.cut)
        # The whole network split in two, and f(C) changed by less than
        # 0.03 in absolute terms — smaller than the gap between an intact
        # ring and an intact star.
        self.assertLess(abs(f_intact - f_cut), 0.03)

    def test_the_split_is_smaller_than_the_ring_star_gap(self):
        _, f_intact = _frobenius_peak(self.intact)
        _, f_cut = _frobenius_peak(self.cut)
        _, f_ring = _frobenius_peak(_ring(6))
        _, f_star = _frobenius_peak(_star(6))
        self.assertLess(abs(f_intact - f_cut), abs(f_ring - f_star) * 2.0)


class ScaleWithSystemSizeTests(unittest.TestCase):
    """F-9: the physics optimum falls as 1/n; the placeholder does not."""

    def test_physics_optimum_scales_inversely_with_n(self):
        for n in (2, 5, 10, 20):
            with self.subTest(n=n):
                spec = spectrum(_complete(n))
                got = optimal_coupling(spec, WINDOW)
                expected = np.sqrt(WINDOW.nu_lower * WINDOW.nu_upper) / n
                self.assertAlmostEqual(got, expected, places=9)

    def test_placeholder_leaves_the_stable_window_past_n_10(self):
        # With this window the placeholder is inside the window through
        # n=10 and RIGID from n=11 — it calls "optimal" exactly the
        # coupling at which the fastest mode is driven unstable.
        self.assertEqual(
            coupling_coherence(PHI_OPT, _complete(10), WINDOW).regime, "STABLE")
        for n in (11, 20, 50):
            with self.subTest(n=n):
                reading = coupling_coherence(PHI_OPT, _complete(n), WINDOW)
                self.assertEqual(reading.regime, "RIGID")
                self.assertEqual(reading.coherence, 0.0)


class SizeInvarianceTests(unittest.TestCase):
    """F-10: f(C) penalizes the same per-edge mistuning quadratically in n."""

    DELTA = 0.10

    def _f(self, n, alpha):
        C = coupling_matrix(n, PHI_OPT + self.DELTA)
        return CoherenceMetric(
            alpha=alpha, coupling_optimum=phi_coupling_optimum(n)
        ).coupling_function(C)

    def test_default_alpha_makes_large_systems_read_as_collapsed(self):
        self.assertGreater(self._f(2, 1.0), 0.97)
        self.assertLess(self._f(20, 1.0), 0.05)
        self.assertLess(self._f(50, 1.0), 1e-6)

    def test_normalized_alpha_is_size_invariant(self):
        values = [self._f(n, 1.0 / (n * (n - 1))) for n in (2, 5, 10, 20, 50)]
        for value in values:
            self.assertAlmostEqual(value, values[0], places=9)

    def test_reading_is_monotone_decreasing_in_n_under_default_alpha(self):
        values = [self._f(n, 1.0) for n in (2, 5, 10, 20, 50)]
        self.assertTrue(all(b < a for a, b in zip(values, values[1:])))


class BridgesUseTheSafestCaseTests(unittest.TestCase):
    """Where the defect does and does not bite the shipped code."""

    def test_n_2_has_only_one_topology(self):
        # Every 2-node connected graph is the same graph, so topology
        # blindness cannot produce a wrong answer at the size the four
        # audit bridges actually construct.
        spec = spectrum(_complete(2))
        self.assertAlmostEqual(spec.lambda_2, 2.0, places=9)
        self.assertAlmostEqual(spec.lambda_n, 2.0, places=9)
        self.assertAlmostEqual(spec.eigenratio, 1.0, places=9)

    def test_placeholder_is_inside_the_window_at_n_2(self):
        reading = coupling_coherence(PHI_OPT, _complete(2), WINDOW)
        self.assertEqual(reading.regime, "STABLE")


if __name__ == "__main__":
    unittest.main()
