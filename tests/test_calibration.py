"""Falsifiable tests for src.measurement.calibration.

Each test pins a claim an adapter makes about the relationship between
measured data and an M(S) term — including the claims that make an
adapter *refuse* to flatter the system it measures.
"""

import unittest

from src.measurement.calibration import (
    ATP_DEATH_FLOOR,
    HORMESIS_MAX_GAIN,
    A_from_recovery_events,
    A_from_timeseries,
    D_effective_number,
    D_model_collapse,
    D_response_diversity,
    L_audited_false_fraction,
    L_combined,
    L_decay_rate,
    L_knowledge_halflife,
    R_e_from_aerobic_scope,
    R_e_from_energy_floor,
    apply_hormesis_ceiling,
    interdependence_penalty,
    may_stability_ceiling,
)


class ProvenanceTests(unittest.TestCase):
    """Every calibration must carry the derivation it used."""

    def _all_calibrations(self):
        return [
            R_e_from_aerobic_scope(100.0, 60.0),
            R_e_from_energy_floor(0.5),
            A_from_recovery_events([2.0, 4.0]),
            apply_hormesis_ceiling(0.5, 1.2),
            D_response_diversity([[1.0, 0.5], [1.0, 1.5]]),
            D_effective_number([0.5, 0.5]),
            D_model_collapse(0.3),
            L_decay_rate(0.2, 2.0),
            L_knowledge_halflife(9.0),
            L_audited_false_fraction(0.36),
            may_stability_ceiling(0.2, 10, 0.2, 1.0),
            interdependence_penalty(4.0),
        ]

    def test_every_adapter_names_a_source(self):
        for cal in self._all_calibrations():
            self.assertTrue(cal.source.strip(), f"{cal.term} has no source")
            self.assertTrue(cal.method.strip(), f"{cal.term} has no method")

    def test_every_value_is_within_unit_interval(self):
        for cal in self._all_calibrations():
            self.assertGreaterEqual(cal.value, 0.0)
            self.assertLessEqual(cal.value, 1.0)

    def test_str_includes_source(self):
        cal = R_e_from_aerobic_scope(100.0, 60.0)
        self.assertIn("Pörtner", str(cal))


class ResonanceEnergyTests(unittest.TestCase):
    def test_zero_aerobic_scope_is_zero_R_e(self):
        # Maintenance consumes the whole throughput: the T_crit condition.
        cal = R_e_from_aerobic_scope(max_metabolic_rate=50.0,
                                     standard_metabolic_rate=50.0)
        self.assertEqual(cal.value, 0.0)

    def test_negative_scope_clamps_to_zero_and_warns(self):
        cal = R_e_from_aerobic_scope(40.0, 60.0)
        self.assertEqual(cal.value, 0.0)
        self.assertIn("BLACK", " ".join(cal.caveats))

    def test_more_headroom_reads_higher(self):
        low = R_e_from_aerobic_scope(100.0, 80.0).value
        high = R_e_from_aerobic_scope(100.0, 20.0).value
        self.assertGreater(high, low)

    def test_energy_below_death_floor_is_zero_not_proportional(self):
        cal = R_e_from_energy_floor(ATP_DEATH_FLOOR - 0.01)
        self.assertEqual(cal.value, 0.0)

    def test_floor_is_a_threshold_not_a_gradient(self):
        # Just above the floor must be far below linear expectation.
        just_above = R_e_from_energy_floor(ATP_DEATH_FLOOR + 0.01).value
        self.assertLess(just_above, 0.16)

    def test_healthy_energy_reads_near_its_fraction(self):
        cal = R_e_from_energy_floor(0.8)
        self.assertAlmostEqual(cal.value, 0.8, places=6)


class AdaptabilityTests(unittest.TestCase):
    def test_faster_recovery_reads_higher(self):
        fast = A_from_recovery_events([1.0, 1.0, 1.0], reference_time=1.0).value
        slow = A_from_recovery_events([10.0, 10.0, 10.0], reference_time=1.0).value
        self.assertGreater(fast, slow)

    def test_no_observed_recoveries_reads_zero_and_says_why(self):
        cal = A_from_recovery_events([])
        self.assertEqual(cal.value, 0.0)
        self.assertIn("absent evidence", " ".join(cal.caveats))

    def test_survivorship_bias_is_disclosed(self):
        cal = A_from_recovery_events([2.0, 3.0])
        self.assertIn("survivorship", " ".join(cal.caveats).lower())

    def test_hormesis_caps_extravagant_gain_claims(self):
        cal = apply_hormesis_ceiling(baseline_A=0.5, claimed_gain=10.0)
        self.assertAlmostEqual(cal.value, 0.5 * HORMESIS_MAX_GAIN, places=9)
        self.assertIn("capped", " ".join(cal.caveats))

    def test_modest_gain_passes_through_uncapped(self):
        cal = apply_hormesis_ceiling(baseline_A=0.4, claimed_gain=1.2)
        self.assertAlmostEqual(cal.value, 0.48, places=9)
        self.assertEqual(cal.caveats, [])

    def test_gain_below_one_is_named_as_a_loss(self):
        cal = apply_hormesis_ceiling(baseline_A=0.5, claimed_gain=0.5)
        self.assertIn("loss of adaptability", " ".join(cal.caveats))

    def test_slow_recovering_series_reads_lower_than_fast(self):
        import random

        def ar1(alpha, seed):
            rng = random.Random(seed)
            out, x = [], 0.0
            for _ in range(120):
                x = alpha * x + rng.gauss(0, 0.1)
                out.append(x)
            return out

        slow = A_from_timeseries(ar1(0.95, 1)).value
        fast = A_from_timeseries(ar1(0.2, 1)).value
        self.assertGreater(fast, slow)

    def test_flat_series_reports_zero_as_absent_evidence(self):
        cal = A_from_timeseries([1.0] * 30)
        self.assertEqual(cal.value, 0.0)
        self.assertIn("not as a measurement of zero", " ".join(cal.caveats))


class DiversityTests(unittest.TestCase):
    def test_synchronized_components_score_near_zero_however_many(self):
        # A hundred components that all move together are one strategy.
        identical = [[1.0, 0.8, 0.6, 0.4] for _ in range(100)]
        cal = D_response_diversity(identical)
        self.assertAlmostEqual(cal.value, 0.0, places=9)

    def test_divergent_responses_score_high(self):
        divergent = [
            [1.0, 0.8, 0.6, 0.4],
            [1.0, 1.2, 1.4, 1.6],
            [1.0, 1.0, 0.9, 1.0],
        ]
        self.assertGreater(D_response_diversity(divergent).value, 0.5)

    def test_response_diversity_beats_counting(self):
        # Same component count, opposite resilience: counting cannot tell
        # these apart and response diversity must.
        synchronized = [[1.0, 0.5, 0.25] for _ in range(4)]
        varied = [
            [1.0, 0.5, 0.25],
            [1.0, 1.5, 2.0],
            [1.0, 1.0, 1.0],
            [1.0, 0.9, 1.3],
        ]
        self.assertLess(D_response_diversity(synchronized).value,
                        D_response_diversity(varied).value)

    def test_effective_independent_responses_is_reported(self):
        cal = D_response_diversity([[1.0, 0.5], [1.0, 1.5]])
        self.assertIn("effective_independent_responses", cal.inputs)

    def test_no_components_is_zero_diversity(self):
        self.assertEqual(D_response_diversity([]).value, 0.0)

    def test_mismatched_series_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            D_response_diversity([[1.0, 2.0], [1.0, 2.0, 3.0]])

    def test_single_point_series_are_rejected(self):
        with self.assertRaises(ValueError):
            D_response_diversity([[1.0], [2.0]])

    def test_unresponsive_components_are_flagged(self):
        cal = D_response_diversity([[1.0, 1.0], [2.0, 2.0]])
        self.assertIn("no component varies", " ".join(cal.caveats))

    def test_even_strategies_beat_concentrated_ones(self):
        even = D_effective_number([0.25, 0.25, 0.25, 0.25]).value
        skewed = D_effective_number([0.97, 0.01, 0.01, 0.01]).value
        self.assertGreater(even, skewed)

    def test_effective_number_discloses_it_is_not_response_diversity(self):
        cal = D_effective_number([0.5, 0.5])
        self.assertIn("respond differently", " ".join(cal.caveats))

    def test_no_viable_strategies_is_zero(self):
        self.assertEqual(D_effective_number([]).value, 0.0)
        self.assertEqual(D_effective_number([0.0, 0.0]).value, 0.0)


class ModelCollapseTests(unittest.TestCase):
    def test_accumulating_real_data_beats_replacing_it(self):
        # The Gerstgrasser 2024 result: accumulation avoids collapse.
        replace = D_model_collapse(0.8, accumulate=False).value
        accumulate = D_model_collapse(0.8, accumulate=True).value
        self.assertGreater(accumulate, replace)

    def test_more_synthetic_data_lowers_diversity_under_replacement(self):
        self.assertGreater(D_model_collapse(0.1).value, D_model_collapse(0.9).value)

    def test_one_percent_contamination_is_flagged(self):
        cal = D_model_collapse(0.02, accumulate=False)
        self.assertIn("Dohmatob", " ".join(cal.caveats))

    def test_clean_replacement_regime_is_full_diversity(self):
        self.assertAlmostEqual(D_model_collapse(0.0, accumulate=False).value, 1.0)


class LossTests(unittest.TestCase):
    def test_faster_loss_reads_higher(self):
        self.assertGreater(L_decay_rate(0.5, 2.0).value, L_decay_rate(0.1, 2.0).value)

    def test_same_loss_over_longer_window_is_a_lower_rate(self):
        self.assertGreater(L_decay_rate(0.2, 1.0).value, L_decay_rate(0.2, 10.0).value)

    def test_no_loss_is_zero_rate(self):
        self.assertEqual(L_decay_rate(0.0, 5.0).value, 0.0)

    def test_zero_window_is_rejected(self):
        with self.assertRaises(ValueError):
            L_decay_rate(0.2, 0.0)

    def test_halflife_matches_the_closed_form(self):
        import math
        cal = L_knowledge_halflife(10.0)
        self.assertAlmostEqual(cal.value, math.log(2) / 10.0, places=9)

    def test_shorter_halflife_is_a_higher_rate(self):
        self.assertGreater(L_knowledge_halflife(2.0).value,
                           L_knowledge_halflife(20.0).value)

    def test_non_positive_halflife_is_rejected(self):
        with self.assertRaises(ValueError):
            L_knowledge_halflife(0.0)

    def test_replication_failure_is_the_loss(self):
        cal = L_audited_false_fraction(0.36)
        self.assertAlmostEqual(cal.value, 0.64, places=9)

    def test_standing_fraction_is_distinguished_from_a_rate(self):
        cal = L_audited_false_fraction(0.36)
        self.assertIn("not a rate", " ".join(cal.caveats))


class CombinedLossTests(unittest.TestCase):
    def test_independent_losses_compound_rather_than_add(self):
        a = L_decay_rate(0.5, 1.0)   # ~0.69
        b = L_decay_rate(0.5, 1.0)
        combined = L_combined([a, b]).value
        self.assertLess(combined, min(1.0, a.value + b.value))
        self.assertGreater(combined, a.value)

    def test_combination_never_exceeds_one(self):
        many = [L_decay_rate(0.6, 1.0) for _ in range(10)]
        self.assertLessEqual(L_combined(many).value, 1.0)

    def test_empty_combination_says_unmeasured_not_absent(self):
        cal = L_combined([])
        self.assertEqual(cal.value, 0.0)
        self.assertIn("unmeasured, not absent", " ".join(cal.caveats))

    def test_wrong_term_is_rejected(self):
        with self.assertRaises(ValueError):
            L_combined([R_e_from_aerobic_scope(100.0, 50.0)])

    def test_component_sources_are_carried_forward(self):
        cal = L_combined([L_knowledge_halflife(9.0)])
        self.assertIn("half-life", " ".join(cal.caveats))


class CouplingBoundTests(unittest.TestCase):
    def test_breaching_mays_bound_gives_zero_margin(self):
        # sigma*sqrt(S*C) = 0.4*sqrt(25*0.3) ~ 1.10 > d = 1.0
        cal = may_stability_ceiling(0.4, 25, 0.3, 1.0)
        self.assertEqual(cal.value, 0.0)
        self.assertIn("bound breached", " ".join(cal.caveats))

    def test_more_components_at_fixed_coupling_shrinks_the_margin(self):
        small = may_stability_ceiling(0.1, 4, 0.3, 1.0).value
        large = may_stability_ceiling(0.1, 64, 0.3, 1.0).value
        self.assertGreater(small, large)

    def test_zero_self_damping_is_rejected(self):
        with self.assertRaises(ValueError):
            may_stability_ceiling(0.2, 10, 0.3, 0.0)

    def test_random_matrix_assumption_is_disclosed(self):
        cal = may_stability_ceiling(0.1, 10, 0.2, 1.0)
        self.assertIn("randomly assembled", " ".join(cal.caveats))

    def test_interdependence_raises_the_failure_threshold(self):
        cal = interdependence_penalty(4.0, coupled_fraction=1.0)
        self.assertAlmostEqual(cal.inputs["isolated_pc"], 0.25, places=9)
        self.assertGreater(cal.inputs["coupled_pc"], cal.inputs["isolated_pc"])

    def test_uncoupled_case_recovers_the_isolated_threshold(self):
        cal = interdependence_penalty(4.0, coupled_fraction=0.0)
        self.assertAlmostEqual(cal.inputs["effective_pc"],
                               cal.inputs["isolated_pc"], places=9)

    def test_partial_coupling_interpolates(self):
        low = interdependence_penalty(4.0, coupled_fraction=0.2).value
        high = interdependence_penalty(4.0, coupled_fraction=0.9).value
        self.assertGreater(low, high)

    def test_first_order_transition_is_disclosed(self):
        cal = interdependence_penalty(4.0)
        self.assertIn("first-order", " ".join(cal.caveats))

    def test_zero_mean_degree_is_rejected(self):
        with self.assertRaises(ValueError):
            interdependence_penalty(0.0)


if __name__ == "__main__":
    unittest.main()
