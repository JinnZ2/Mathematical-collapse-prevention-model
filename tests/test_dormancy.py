"""Falsifiable tests for src.measurement.dormancy.

The claims worth pinning: folding preserves ratios exactly and magnitude
not at all, the option to fold closes before the system dies, waiting
costs viability on a clock, over-compression is charged rather than
rewarded, and a seed's absence is reported as absent evidence rather
than as proof of death.
"""

import unittest

from src.measurement.dormancy import (
    DEFAULT_FOLD_COST,
    MAX_USEFUL_RESIDUAL,
    MIN_VIABLE_RESIDUAL,
    SEED_TERMS,
    SeedState,
    assess_dormancy,
    fold,
    fold_window,
    format_dormancy,
    unfold,
    viability,
)

HEALTHY = dict(resonance_energy=0.40, adaptability=0.30,
               diversity=0.55, coupling=0.70)


class FoldWindowTests(unittest.TestCase):
    def test_window_is_open_while_energy_exceeds_the_fold_cost(self):
        self.assertTrue(fold_window(0.8).open)

    def test_window_closes_below_the_fold_cost(self):
        window = fold_window(DEFAULT_FOLD_COST / 2)
        self.assertFalse(window.open)
        self.assertIn("expired before the system did", " ".join(window.warnings))

    def test_closing_happens_before_the_system_reaches_zero(self):
        # The point of the window: the option is gone while there is
        # still energy left, not at the moment of death.
        self.assertFalse(fold_window(0.05).open)
        self.assertGreater(0.05, 0.0)

    def test_narrow_window_is_flagged_before_it_closes(self):
        window = fold_window(DEFAULT_FOLD_COST * 1.5)
        self.assertTrue(window.open)
        self.assertIn("NARROW", " ".join(window.warnings))

    def test_invalid_cost_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            fold_window(0.5, fold_cost_fraction=1.5)


class FoldTests(unittest.TestCase):
    def test_proportions_sum_to_one(self):
        seed = fold(**HEALTHY)
        self.assertAlmostEqual(sum(seed.proportions.values()), 1.0, places=12)

    def test_all_structural_terms_are_carried(self):
        seed = fold(**HEALTHY)
        self.assertEqual(set(seed.proportions), set(SEED_TERMS))

    def test_ratios_are_preserved_exactly(self):
        seed = fold(**HEALTHY)
        self.assertAlmostEqual(
            seed.proportions["coupling"] / seed.proportions["adaptability"],
            HEALTHY["coupling"] / HEALTHY["adaptability"],
            places=12,
        )

    def test_magnitude_is_recorded_but_not_preserved_in_the_proportions(self):
        small = fold(**HEALTHY)
        big = fold(**{k: v * 100 for k, v in HEALTHY.items()})
        # Same shape, different totals: the seed is scale-free.
        for term in SEED_TERMS:
            self.assertAlmostEqual(small.proportions[term],
                                   big.proportions[term], places=12)
        self.assertAlmostEqual(big.conserved_total,
                               small.conserved_total * 100, places=9)

    def test_folding_states_what_it_destroys(self):
        seed = fold(**HEALTHY)
        joined = " ".join(seed.lost)
        self.assertIn("absolute magnitude", joined)
        self.assertIn("history", joined)

    def test_folding_cites_both_source_frameworks(self):
        seed = fold(**HEALTHY)
        joined = " ".join(seed.provenance)
        self.assertIn("Seed-physics", joined)
        self.assertIn("Mandala-Computing", joined)

    def test_metric_signature_is_carried_verbatim(self):
        seed = fold(**HEALTHY, metric_signature={"coupling_optimum": "phi"})
        self.assertEqual(seed.metric_signature["coupling_optimum"], "phi")

    def test_empty_structure_cannot_be_folded(self):
        # This is the case where BLACK means exactly what it says.
        with self.assertRaises(ValueError) as ctx:
            fold(resonance_energy=0.0, adaptability=0.0,
                 diversity=0.0, coupling=0.0)
        self.assertIn("BLACK means what it says", str(ctx.exception))

    def test_closed_window_refuses_the_fold(self):
        with self.assertRaises(ValueError):
            fold(resonance_energy=0.01, adaptability=0.3,
                 diversity=0.5, coupling=0.7)

    def test_term_already_at_zero_is_recorded_as_unrecoverable(self):
        seed = fold(resonance_energy=0.4, adaptability=0.0,
                    diversity=0.55, coupling=0.7)
        self.assertTrue(seed.is_degenerate)
        self.assertIn("re-expands to zero", " ".join(seed.lost))

    def test_seed_rejects_proportions_that_do_not_sum_to_one(self):
        with self.assertRaises(ValueError):
            SeedState(proportions={"a": 0.3, "b": 0.3}, conserved_total=1.0)


class ViabilityDecayTests(unittest.TestCase):
    """Ellis & Roberts: duration is bought, and the price is finite."""

    def test_viability_falls_monotonically_with_time(self):
        seed = fold(**HEALTHY, residual_activity=0.05)
        previous = 1.1
        for elapsed in (0, 1000, 10000, 100000, 1000000):
            current = viability(seed, float(elapsed), stress=10.0).viable_fraction
            self.assertLessEqual(current, previous)
            previous = current

    def test_stress_shortens_the_time_constant(self):
        seed = fold(**HEALTHY)
        calm = viability(seed, 0.0, stress=0.0).sigma
        stressed = viability(seed, 0.0, stress=40.0).sigma
        self.assertGreater(calm, stressed)

    def test_lower_residual_activity_buys_duration(self):
        wet = fold(**HEALTHY, residual_activity=0.06)
        dry = fold(**HEALTHY, residual_activity=0.03)
        self.assertGreater(viability(dry, 0.0).sigma, viability(wet, 0.0).sigma)

    def test_a_stressed_seed_can_outlive_its_viability(self):
        seed = fold(**HEALTHY)
        self.assertEqual(viability(seed, 100000.0, stress=40.0).flag, "NONVIABLE")

    def test_flags_progress_through_degrading_to_nonviable(self):
        # sigma is ~1080 periods at this residual activity and stress, so
        # these three sit at roughly 0, 3 and 30 time constants.
        seed = fold(**HEALTHY)
        flags = [viability(seed, float(p), stress=20.0).flag
                 for p in (0, 3000, 30000)]
        self.assertEqual(flags, ["VIABLE", "DEGRADING", "NONVIABLE"])

    def test_seed_constants_are_disclosed_as_an_analogy(self):
        seed = fold(**HEALTHY)
        self.assertIn("analogy, not a measurement",
                      " ".join(viability(seed, 10.0).warnings))

    def test_reading_cites_ellis_and_roberts(self):
        self.assertIn("Ellis & Roberts 1980",
                      viability(fold(**HEALTHY), 10.0).source)

    def test_negative_elapsed_is_rejected(self):
        with self.assertRaises(ValueError):
            viability(fold(**HEALTHY), -1.0)


class OverCompressionTests(unittest.TestCase):
    """Compressing past the floor is loss, not better compression."""

    def test_below_the_floor_is_charged_not_rewarded(self):
        at_floor = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL)
        crushed = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL / 4)
        self.assertGreater(viability(at_floor, 1000.0).viable_fraction,
                           viability(crushed, 1000.0).viable_fraction)

    def test_drying_below_the_floor_does_not_extend_sigma(self):
        at_floor = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL)
        crushed = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL / 10)
        self.assertAlmostEqual(viability(at_floor, 0.0).sigma,
                               viability(crushed, 0.0).sigma, places=9)

    def test_over_compression_is_named_in_the_warnings(self):
        crushed = fold(**HEALTHY, residual_activity=0.001)
        self.assertIn("over-compression",
                      " ".join(viability(crushed, 10.0).warnings).lower())

    def test_storing_too_wet_is_flagged(self):
        wet = fold(**HEALTHY, residual_activity=MAX_USEFUL_RESIDUAL * 2)
        self.assertIn("storing wetter", " ".join(viability(wet, 10.0).warnings))

    def test_fold_notes_the_floor_when_crossed(self):
        seed = fold(**HEALTHY, residual_activity=0.005)
        self.assertIn("floor", " ".join(seed.provenance))


class UnfoldTests(unittest.TestCase):
    def test_round_trip_at_the_original_total_recovers_the_inputs(self):
        seed = fold(**HEALTHY)
        revived = unfold(seed, available_energy=seed.conserved_total)
        for term, original in HEALTHY.items():
            self.assertAlmostEqual(revived[term], original, places=12)

    def test_re_expansion_scales_to_what_is_available(self):
        seed = fold(**HEALTHY)
        small = unfold(seed, available_energy=seed.conserved_total / 4)
        self.assertAlmostEqual(sum(small.values()),
                               seed.conserved_total / 4, places=12)

    def test_proportions_survive_a_change_of_scale(self):
        seed = fold(**HEALTHY)
        revived = unfold(seed, available_energy=0.2)
        self.assertAlmostEqual(
            revived["coupling"] / revived["adaptability"],
            HEALTHY["coupling"] / HEALTHY["adaptability"],
            places=12,
        )

    def test_partial_viability_re_expands_smaller_not_distorted(self):
        seed = fold(**HEALTHY)
        reading = viability(seed, 3000.0, stress=20.0)
        self.assertEqual(reading.flag, "DEGRADING")
        revived = unfold(seed, available_energy=1.0, viability_reading=reading)
        self.assertLess(sum(revived.values()), 1.0)
        self.assertAlmostEqual(
            revived["diversity"] / revived["coupling"],
            HEALTHY["diversity"] / HEALTHY["coupling"],
            places=12,
        )

    def test_nonviable_seed_cannot_be_re_expanded(self):
        seed = fold(**HEALTHY)
        dead = viability(seed, 1000000.0, stress=40.0)
        with self.assertRaises(ValueError):
            unfold(seed, available_energy=1.0, viability_reading=dead)

    def test_zero_energy_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            unfold(fold(**HEALTHY), available_energy=0.0)

    def test_degenerate_term_re_expands_to_zero(self):
        seed = fold(resonance_energy=0.4, adaptability=0.0,
                    diversity=0.55, coupling=0.7)
        revived = unfold(seed, available_energy=10.0)
        self.assertEqual(revived["adaptability"], 0.0)


class DormancyAssessmentTests(unittest.TestCase):
    """The structural channel that stands alongside a BLACK verdict."""

    def test_fresh_seed_reads_dormant_not_dead(self):
        reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=10.0)
        self.assertEqual(reading.state, "DORMANT")

    def test_dormant_reading_names_the_false_positive_it_corrects(self):
        reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=10.0)
        self.assertIn("no flux, not because there is no structure",
                      " ".join(reading.warnings))

    def test_expired_seed_reads_lost_and_concedes_black(self):
        reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=1000000.0,
                                  stress=40.0)
        self.assertEqual(reading.state, "SEED_LOST")
        self.assertIn("BLACK is now the correct reading",
                      " ".join(reading.warnings))

    def test_partly_degraded_seed_reads_revivable(self):
        reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=3000.0,
                                  stress=20.0)
        self.assertEqual(reading.state, "REVIVABLE")

    def test_no_seed_is_absent_evidence_not_proof_of_death(self):
        reading = assess_dormancy(None)
        self.assertEqual(reading.state, "NEVER_FOLDED")
        joined = " ".join(reading.warnings)
        self.assertIn("not proof of death", joined)
        self.assertIn("not evidence of dormancy either", joined)

    def test_format_includes_proportions_losses_and_the_disclaimer(self):
        text = format_dormancy(assess_dormancy(fold(**HEALTHY), 10.0))
        self.assertIn("preserved proportions", text)
        self.assertIn("NOT PRESERVED BY FOLDING", text)
        self.assertIn("Whether waiting is worth it is not a measurement", text)

    def test_format_handles_the_never_folded_case(self):
        text = format_dormancy(assess_dormancy(None))
        self.assertIn("NEVER_FOLDED", text)


if __name__ == "__main__":
    unittest.main()
