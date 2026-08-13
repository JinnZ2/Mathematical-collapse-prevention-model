"""Falsifiable tests for src.measurement.coupling_physics.

The central claim is that f(C)'s interior optimum is *derived* from
synchronization stability rather than asserted by choosing a C*. These
tests pin it against Laplacian spectra with exactly known closed forms,
and against the two boundaries the physics predicts: the slowest mode
failing to lock, and the fastest mode going unstable.
"""

import math
import unittest

import numpy as np

from src.measurement.coupling_physics import (
    MSFWindow,
    coupling_coherence,
    format_coupling,
    laplacian,
    optimal_coupling,
    spectrum,
    synchronizable,
)

# Bounded window -> Class III -> a real interior optimum exists.
CLASS_III = MSFWindow(nu_lower=0.2, nu_upper=4.0, system="test dynamics")
# Unbounded above -> Class II -> a threshold, not an optimum.
CLASS_II = MSFWindow(nu_lower=0.2, system="test dynamics")


def complete_graph(n):
    A = np.ones((n, n)) - np.eye(n)
    return A


def star_graph(n):
    A = np.zeros((n, n))
    A[0, 1:] = 1.0
    A[1:, 0] = 1.0
    return A


def cycle_graph(n):
    A = np.zeros((n, n))
    for i in range(n):
        A[i, (i + 1) % n] = 1.0
        A[(i + 1) % n, i] = 1.0
    return A


def two_components():
    return np.array([
        [0, 1, 0, 0],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ], dtype=float)


class MSFWindowTests(unittest.TestCase):
    def test_bounded_window_is_class_three(self):
        self.assertEqual(CLASS_III.msf_class, "III")
        self.assertTrue(CLASS_III.has_interior_optimum)

    def test_unbounded_window_is_class_two(self):
        self.assertEqual(CLASS_II.msf_class, "II")
        self.assertFalse(CLASS_II.has_interior_optimum)

    def test_width_ratio(self):
        self.assertAlmostEqual(CLASS_III.width_ratio, 20.0, places=9)
        self.assertTrue(math.isinf(CLASS_II.width_ratio))

    def test_non_positive_lower_crossing_is_rejected(self):
        with self.assertRaises(ValueError):
            MSFWindow(nu_lower=0.0)

    def test_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            MSFWindow(nu_lower=4.0, nu_upper=0.2)


class LaplacianTests(unittest.TestCase):
    def test_rows_sum_to_zero(self):
        L = laplacian(cycle_graph(6))
        self.assertTrue(np.allclose(L.sum(axis=1), 0.0))

    def test_asymmetric_adjacency_is_rejected(self):
        A = np.array([[0.0, 1.0], [0.0, 0.0]])
        with self.assertRaises(ValueError):
            laplacian(A)

    def test_negative_weights_are_rejected(self):
        A = np.array([[0.0, -1.0], [-1.0, 0.0]])
        with self.assertRaises(ValueError):
            laplacian(A)

    def test_single_node_is_rejected(self):
        with self.assertRaises(ValueError):
            laplacian(np.zeros((1, 1)))

    def test_non_square_is_rejected(self):
        with self.assertRaises(ValueError):
            laplacian(np.zeros((2, 3)))

    def test_self_loops_are_ignored(self):
        plain = laplacian(cycle_graph(4))
        looped = cycle_graph(4)
        np.fill_diagonal(looped, 5.0)
        self.assertTrue(np.allclose(plain, laplacian(looped)))


class SpectrumTests(unittest.TestCase):
    """Checked against closed-form Laplacian spectra."""

    def test_complete_graph_eigenratio_is_one(self):
        # K_n has eigenvalues 0 and n (n-1 times): perfectly uniform.
        spec = spectrum(complete_graph(6))
        self.assertAlmostEqual(spec.lambda_2, 6.0, places=9)
        self.assertAlmostEqual(spec.lambda_n, 6.0, places=9)
        self.assertAlmostEqual(spec.eigenratio, 1.0, places=9)

    def test_star_eigenratio_equals_node_count(self):
        # S_n has eigenvalues 0, 1 (n-2 times), n.
        spec = spectrum(star_graph(6))
        self.assertAlmostEqual(spec.lambda_2, 1.0, places=9)
        self.assertAlmostEqual(spec.lambda_n, 6.0, places=9)
        self.assertAlmostEqual(spec.eigenratio, 6.0, places=9)

    def test_cycle_matches_closed_form(self):
        # C_n has eigenvalues 2 - 2 cos(2 pi k / n).
        n = 7
        spec = spectrum(cycle_graph(n))
        expected = sorted(2 - 2 * math.cos(2 * math.pi * k / n) for k in range(n))
        for got, want in zip(spec.eigenvalues, expected):
            self.assertAlmostEqual(got, want, places=9)

    def test_larger_star_is_harder_to_synchronize_than_complete_graph(self):
        self.assertGreater(spectrum(star_graph(8)).eigenratio,
                           spectrum(complete_graph(8)).eigenratio)

    def test_disconnected_graph_has_zero_algebraic_connectivity(self):
        spec = spectrum(two_components())
        self.assertEqual(spec.lambda_2, 0.0)
        self.assertFalse(spec.connected)
        self.assertEqual(spec.n_components, 2)
        self.assertTrue(math.isinf(spec.eigenratio))

    def test_disconnection_is_reported_as_structural(self):
        spec = spectrum(two_components())
        self.assertIn("not a tuning problem", " ".join(spec.warnings))

    def test_exactly_one_zero_eigenvalue_when_connected(self):
        spec = spectrum(cycle_graph(5))
        self.assertEqual(spec.n_components, 1)
        self.assertTrue(spec.connected)


class SynchronizabilityCriterionTests(unittest.TestCase):
    """lambda_N / lambda_2 < nu_2 / nu_1 (Barahona & Pecora 2002)."""

    def test_low_eigenratio_network_is_synchronizable(self):
        self.assertTrue(synchronizable(spectrum(complete_graph(6)), CLASS_III))

    def test_eigenratio_above_window_ratio_is_not_synchronizable(self):
        # A star with more nodes than the window ratio cannot fit.
        spec = spectrum(star_graph(25))
        self.assertGreater(spec.eigenratio, CLASS_III.width_ratio)
        self.assertFalse(synchronizable(spec, CLASS_III))

    def test_class_two_dynamics_tolerate_any_eigenratio(self):
        spec = spectrum(star_graph(50))
        self.assertTrue(synchronizable(spec, CLASS_II))

    def test_disconnected_is_never_synchronizable(self):
        self.assertFalse(synchronizable(spectrum(two_components()), CLASS_III))
        self.assertFalse(synchronizable(spectrum(two_components()), CLASS_II))

    def test_unsynchronizable_network_reports_that_tuning_cannot_fix_it(self):
        reading = coupling_coherence(1.0, star_graph(25), CLASS_III)
        self.assertEqual(reading.regime, "NO_STABLE_WINDOW")
        self.assertEqual(reading.coherence, 0.0)
        self.assertIn("not a different coupling strength", " ".join(reading.notes))


class OptimalCouplingTests(unittest.TestCase):
    def test_matches_the_geometric_centre_formula(self):
        spec = spectrum(cycle_graph(5))
        expected = math.sqrt(
            CLASS_III.nu_lower * CLASS_III.nu_upper / (spec.lambda_2 * spec.lambda_n)
        )
        self.assertAlmostEqual(optimal_coupling(spec, CLASS_III), expected, places=12)

    def test_optimum_equalizes_the_two_log_margins(self):
        spec = spectrum(cycle_graph(5))
        sigma = optimal_coupling(spec, CLASS_III)
        lower = math.log(sigma * spec.lambda_2 / CLASS_III.nu_lower)
        upper = math.log(CLASS_III.nu_upper / (sigma * spec.lambda_n))
        self.assertAlmostEqual(lower, upper, places=12)

    def test_class_two_has_no_optimum(self):
        self.assertIsNone(optimal_coupling(spectrum(cycle_graph(5)), CLASS_II))

    def test_unsynchronizable_network_has_no_optimum(self):
        self.assertIsNone(optimal_coupling(spectrum(star_graph(25)), CLASS_III))

    def test_margin_squared_is_window_ratio_over_eigenratio(self):
        spec = spectrum(cycle_graph(5))
        reading = coupling_coherence(optimal_coupling(spec, CLASS_III),
                                     cycle_graph(5), CLASS_III)
        self.assertAlmostEqual(
            reading.margin ** 2,
            CLASS_III.width_ratio / spec.eigenratio,
            places=9,
        )


class InteriorOptimumTests(unittest.TestCase):
    """The claim the core module could not express: f(C) really peaks."""

    def test_coherence_is_one_at_the_optimum(self):
        graph = cycle_graph(5)
        sigma = optimal_coupling(spectrum(graph), CLASS_III)
        self.assertAlmostEqual(
            coupling_coherence(sigma, graph, CLASS_III).coherence, 1.0, places=9)

    def test_both_extremes_are_penalized(self):
        graph = cycle_graph(5)
        sigma = optimal_coupling(spectrum(graph), CLASS_III)
        peak = coupling_coherence(sigma, graph, CLASS_III).coherence
        weak = coupling_coherence(sigma / 3, graph, CLASS_III).coherence
        strong = coupling_coherence(sigma * 3, graph, CLASS_III).coherence
        self.assertGreater(peak, weak)
        self.assertGreater(peak, strong)

    def test_coherence_rises_then_falls_across_the_window(self):
        graph = cycle_graph(5)
        spec = spectrum(graph)
        lo = CLASS_III.nu_lower / spec.lambda_2
        hi = CLASS_III.nu_upper / spec.lambda_n
        sigmas = [lo + (hi - lo) * i / 40 for i in range(1, 40)]
        values = [coupling_coherence(s, graph, CLASS_III).coherence for s in sigmas]
        peak_index = values.index(max(values))
        self.assertTrue(all(a <= b + 1e-12
                            for a, b in zip(values[:peak_index], values[1:peak_index + 1])))
        self.assertTrue(all(a >= b - 1e-12
                            for a, b in zip(values[peak_index:], values[peak_index + 1:])))

    def test_too_weak_names_the_slowest_mode(self):
        graph = cycle_graph(5)
        spec = spectrum(graph)
        reading = coupling_coherence(CLASS_III.nu_lower / spec.lambda_2 / 2,
                                     graph, CLASS_III)
        self.assertEqual(reading.regime, "FRAGMENTED")
        self.assertIn("slowest mode never locks", " ".join(reading.notes))

    def test_too_strong_names_the_fastest_mode(self):
        graph = cycle_graph(5)
        spec = spectrum(graph)
        reading = coupling_coherence(CLASS_III.nu_upper / spec.lambda_n * 2,
                                     graph, CLASS_III)
        self.assertEqual(reading.regime, "RIGID")
        self.assertIn("fastest mode is driven unstable", " ".join(reading.notes))

    def test_coherence_is_bounded_to_the_unit_interval(self):
        graph = cycle_graph(6)
        for sigma in (0.0, 0.01, 0.2, 0.5, 1.0, 5.0, 100.0):
            c = coupling_coherence(sigma, graph, CLASS_III).coherence
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0)

    def test_negative_coupling_is_rejected(self):
        with self.assertRaises(ValueError):
            coupling_coherence(-1.0, cycle_graph(4), CLASS_III)


class ClassTwoTests(unittest.TestCase):
    """Physics gives a threshold here, not an optimum. Do not invent one."""

    def test_above_threshold_is_full_coherence(self):
        graph = cycle_graph(5)
        spec = spectrum(graph)
        threshold = CLASS_II.nu_lower / spec.lambda_2
        self.assertEqual(
            coupling_coherence(threshold * 10, graph, CLASS_II).coherence, 1.0)

    def test_more_coupling_is_never_penalized(self):
        graph = cycle_graph(5)
        a = coupling_coherence(10.0, graph, CLASS_II).coherence
        b = coupling_coherence(1000.0, graph, CLASS_II).coherence
        self.assertEqual(a, b)

    def test_below_threshold_is_still_fragmented(self):
        graph = cycle_graph(5)
        spec = spectrum(graph)
        reading = coupling_coherence(CLASS_II.nu_lower / spec.lambda_2 / 2,
                                     graph, CLASS_II)
        self.assertEqual(reading.regime, "FRAGMENTED")

    def test_binary_treatment_is_disclosed(self):
        reading = coupling_coherence(10.0, cycle_graph(5), CLASS_II)
        self.assertIn("invented gradient", " ".join(reading.notes))

    def test_no_optimal_sigma_is_reported(self):
        self.assertIsNone(coupling_coherence(10.0, cycle_graph(5), CLASS_II).sigma_optimal)


class DisconnectedNetworkTests(unittest.TestCase):
    def test_no_coupling_strength_helps(self):
        for sigma in (0.01, 0.4, 10.0, 1000.0):
            reading = coupling_coherence(sigma, two_components(), CLASS_III)
            self.assertEqual(reading.coherence, 0.0)
            self.assertEqual(reading.regime, "FRAGMENTED_STRUCTURALLY")

    def test_distinguished_from_merely_undercoupled(self):
        structural = coupling_coherence(0.4, two_components(), CLASS_III)
        tunable = coupling_coherence(0.001, cycle_graph(5), CLASS_III)
        self.assertNotEqual(structural.regime, tunable.regime)
        self.assertIn("no path", " ".join(structural.notes))


class ProvenanceTests(unittest.TestCase):
    def test_readings_cite_their_derivation(self):
        reading = coupling_coherence(0.4, cycle_graph(5), CLASS_III)
        self.assertIn("Pecora & Carroll 1998", reading.source)
        self.assertIn("Barahona & Pecora 2002", reading.source)
        self.assertIn("Huang et al. 2009", reading.source)

    def test_format_reports_regime_window_and_disclaimer(self):
        text = format_coupling(coupling_coherence(0.4, cycle_graph(5), CLASS_III))
        self.assertIn("stable window", text)
        self.assertIn("optimal sigma", text)
        self.assertIn("Some systems should not synchronize", text)


if __name__ == "__main__":
    unittest.main()
