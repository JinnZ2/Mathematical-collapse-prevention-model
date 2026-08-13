"""Falsifiable tests for src.measurement.uncertainty.

The load-bearing claims here are that the interval bounds are *tight*
(every value inside is attainable and nothing outside is), that the
verdict is reported as undetermined exactly when the evidence leaves it
open, and that the Monte Carlo layer never contradicts the guaranteed
bounds it is sampling inside.
"""

import random
import unittest

from src.measurement.calibration import L_decay_rate, L_knowledge_halflife
from src.measurement.uncertainty import (
    Interval,
    MonteCarloReading,
    UncertainState,
    _as_args,
    _m_of,
    coupling_interval,
    format_uncertainty,
    from_calibrations,
    from_relative,
    monte_carlo,
    percentile,
    point,
    propagate,
)


def _state(**overrides):
    base = dict(
        resonance_energy=Interval(0.6, 0.9),
        adaptability=Interval(0.5, 0.9),
        diversity=Interval(0.5, 0.9),
        coupling=Interval(0.75, 0.95),
        loss_rate=Interval(0.15, 0.35),
    )
    base.update(overrides)
    return UncertainState(**base)


class IntervalTests(unittest.TestCase):
    def test_inverted_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            Interval(0.8, 0.2)

    def test_mode_outside_bounds_is_rejected(self):
        with self.assertRaises(ValueError):
            Interval(0.0, 1.0, mode=1.5)

    def test_width_and_midpoint(self):
        iv = Interval(0.2, 0.8)
        self.assertAlmostEqual(iv.width, 0.6, places=9)
        self.assertAlmostEqual(iv.midpoint, 0.5, places=9)

    def test_point_interval_has_no_width(self):
        self.assertTrue(point(0.4).is_point)
        self.assertEqual(point(0.4).width, 0.0)

    def test_contains(self):
        iv = Interval(0.2, 0.8)
        self.assertTrue(iv.contains(0.5))
        self.assertFalse(iv.contains(0.9))

    def test_from_relative_clamps_at_zero(self):
        iv = from_relative(0.1, 2.0)
        self.assertEqual(iv.lo, 0.0)
        self.assertAlmostEqual(iv.hi, 0.3, places=9)

    def test_from_relative_rejects_negative_uncertainty(self):
        with self.assertRaises(ValueError):
            from_relative(0.5, -0.1)


class FromCalibrationsTests(unittest.TestCase):
    def test_disagreement_between_derivations_becomes_the_interval(self):
        a = L_decay_rate(0.22, 2.0)
        b = L_knowledge_halflife(9.0)
        iv = from_calibrations([a, b])
        self.assertAlmostEqual(iv.lo, min(a.value, b.value), places=9)
        self.assertAlmostEqual(iv.hi, max(a.value, b.value), places=9)

    def test_both_sources_are_carried(self):
        iv = from_calibrations([L_decay_rate(0.22, 2.0), L_knowledge_halflife(9.0)])
        self.assertIn("half-life", iv.source)
        self.assertIn("link rot", iv.source)

    def test_single_calibration_gives_a_point_interval(self):
        self.assertTrue(from_calibrations([L_knowledge_halflife(9.0)]).is_point)

    def test_mixed_terms_are_rejected(self):
        from src.measurement.calibration import R_e_from_aerobic_scope
        with self.assertRaises(ValueError):
            from_calibrations([L_knowledge_halflife(9.0),
                               R_e_from_aerobic_scope(100.0, 50.0)])

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            from_calibrations([])

    def test_term_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            from_calibrations([L_knowledge_halflife(9.0)], term="R_e")


class CouplingIntervalTests(unittest.TestCase):
    def test_takes_extremes_over_candidates_not_endpoints(self):
        # f(C) is non-monotonic, so a mid-range candidate can be the peak.
        # A fake metric standing in for the real coupling function makes
        # that explicit: the highest value is at the middle candidate.
        class _Metric:
            def coupling_function(self, C):
                return {0: 0.2, 1: 0.9, 2: 0.3}[C]

        iv = coupling_interval(_Metric(), [0, 1, 2])
        self.assertAlmostEqual(iv.lo, 0.2, places=9)
        self.assertAlmostEqual(iv.hi, 0.9, places=9)

    def test_real_coupling_function_is_accepted(self):
        import numpy as np
        from src.core.coherence_metric import PHI, CoherenceMetric

        metric = CoherenceMetric()
        matrices = [np.array([[1 / PHI, c], [c, 1 / PHI]]) for c in (0.0, 0.3, 0.9)]
        iv = coupling_interval(metric, matrices)
        self.assertGreaterEqual(iv.hi, iv.lo)
        self.assertLessEqual(iv.hi, 1.0)

    def test_empty_candidate_set_is_rejected(self):
        class _Metric:
            def coupling_function(self, C):
                return 0.5

        with self.assertRaises(ValueError):
            coupling_interval(_Metric(), [])


class StateValidationTests(unittest.TestCase):
    def test_negative_gain_term_is_rejected(self):
        with self.assertRaises(ValueError):
            _state(diversity=Interval(-0.1, 0.5))

    def test_negative_loss_is_allowed(self):
        # A negative loss rate is strange but not a monotonicity violation.
        state = _state(loss_rate=Interval(-0.1, 0.2))
        self.assertGreater(propagate(state).m_interval.hi, 0)

    def test_is_certain_detects_all_point_inputs(self):
        certain = UncertainState(
            resonance_energy=point(0.9), adaptability=point(0.85),
            diversity=point(0.8), coupling=point(0.9), loss_rate=point(0.1),
        )
        self.assertTrue(certain.is_certain)
        self.assertFalse(_state().is_certain)


class IntervalPropagationTests(unittest.TestCase):
    def test_bounds_are_sound_no_interior_point_escapes(self):
        state = _state()
        reading = propagate(state)
        rng = random.Random(4)
        intervals = state.intervals()
        for _ in range(3000):
            drawn = {n: rng.uniform(iv.lo, iv.hi) for n, iv in intervals.items()}
            m = _m_of(**_as_args(drawn))
            self.assertGreaterEqual(m, reading.m_interval.lo - 1e-12)
            self.assertLessEqual(m, reading.m_interval.hi + 1e-12)

    def test_bounds_are_tight_both_extremes_are_attained(self):
        state = _state()
        reading = propagate(state)
        lowest = _m_of(state.resonance_energy.lo, state.adaptability.lo,
                       state.diversity.lo, state.coupling.lo, state.loss_rate.hi)
        highest = _m_of(state.resonance_energy.hi, state.adaptability.hi,
                        state.diversity.hi, state.coupling.hi, state.loss_rate.lo)
        self.assertAlmostEqual(reading.m_interval.lo, lowest, places=12)
        self.assertAlmostEqual(reading.m_interval.hi, highest, places=12)

    def test_point_inputs_collapse_to_the_point_estimate(self):
        certain = UncertainState(
            resonance_energy=point(0.9), adaptability=point(0.85),
            diversity=point(0.8), coupling=point(0.9), loss_rate=point(0.1),
        )
        reading = propagate(certain)
        self.assertAlmostEqual(reading.m_interval.width, 0.0, places=12)
        self.assertAlmostEqual(reading.m_interval.lo,
                               0.9 * 0.85 * 0.8 * 0.9 - 0.1, places=12)

    def test_point_inputs_are_flagged_as_propagating_nothing(self):
        certain = UncertainState(
            resonance_energy=point(0.9), adaptability=point(0.85),
            diversity=point(0.8), coupling=point(0.9), loss_rate=point(0.1),
        )
        self.assertIn("propagates no uncertainty",
                      " ".join(propagate(certain).warnings))

    def test_wider_inputs_give_wider_output(self):
        narrow = propagate(_state(loss_rate=Interval(0.24, 0.26))).m_interval.width
        wide = propagate(_state(loss_rate=Interval(0.05, 0.45))).m_interval.width
        self.assertGreater(wide, narrow)


class VerdictDeterminationTests(unittest.TestCase):
    def test_green_point_estimate_can_hide_an_undetermined_verdict(self):
        state = _state()
        midpoints = {k: v.midpoint for k, v in state.intervals().items()}
        self.assertGreater(_m_of(**_as_args(midpoints)), 0)   # midpoint is GREEN
        reading = propagate(state)
        self.assertFalse(reading.verdict_determined)
        self.assertIn("RED", reading.possible_signals)

    def test_clearly_healthy_system_is_determined_green(self):
        state = _state(
            resonance_energy=Interval(0.85, 0.95), adaptability=Interval(0.85, 0.95),
            diversity=Interval(0.85, 0.95), coupling=Interval(0.9, 0.95),
            loss_rate=Interval(0.01, 0.05),
        )
        reading = propagate(state)
        self.assertTrue(reading.verdict_determined)
        self.assertEqual(reading.possible_signals, ["GREEN"])

    def test_clearly_collapsing_system_is_determined_red(self):
        state = _state(
            resonance_energy=Interval(0.05, 0.15), adaptability=Interval(0.05, 0.15),
            diversity=Interval(0.05, 0.15), coupling=Interval(0.2, 0.4),
            loss_rate=Interval(0.6, 0.9),
        )
        reading = propagate(state)
        self.assertTrue(reading.verdict_determined)
        self.assertEqual(reading.possible_signals, ["RED"])

    def test_structural_term_reaching_zero_makes_black_reachable(self):
        # BLACK is triggered by a structural term hitting zero, which need
        # not coincide with the M(S) extreme — so corners must be scanned,
        # not just the two endpoints of the M(S) interval.
        reading = propagate(_state(diversity=Interval(0.0, 0.9)))
        self.assertIn("BLACK", reading.possible_signals)

    def test_undetermined_verdict_is_named_in_the_warnings(self):
        reading = propagate(_state())
        self.assertIn("VERDICT UNDETERMINED", " ".join(reading.warnings))

    def test_interval_spanning_zero_is_reported(self):
        reading = propagate(_state())
        self.assertTrue(reading.m_interval.contains(0.0))
        self.assertIn("spans zero", " ".join(reading.warnings))

    def test_history_enables_the_trajectory_bands(self):
        # With a falling history a marginal system can reach AMBER, which
        # is unreachable without history.
        state = _state(
            resonance_energy=Interval(0.7, 0.75), adaptability=Interval(0.7, 0.75),
            diversity=Interval(0.7, 0.75), coupling=Interval(0.8, 0.85),
            loss_rate=Interval(0.1, 0.12),
        )
        without = propagate(state).possible_signals
        with_history = propagate(state, history=[0.9, 0.7, 0.5, 0.35]).possible_signals
        self.assertEqual(without, ["GREEN"])
        self.assertIn("AMBER", with_history)


class ContributionTests(unittest.TestCase):
    def test_contributions_are_ranked_by_magnitude(self):
        contributions = propagate(_state()).contributions
        spans = [span for _, span in contributions]
        self.assertEqual(spans, sorted(spans, reverse=True))

    def test_point_input_contributes_nothing(self):
        reading = propagate(_state(coupling=point(0.9)))
        self.assertEqual(dict(reading.contributions)["coupling"], 0.0)

    def test_widest_input_dominates(self):
        # loss_rate enters linearly with slope 1, so a wide loss interval
        # dominates a narrow one elsewhere.
        reading = propagate(_state(loss_rate=Interval(0.0, 0.9),
                                   coupling=Interval(0.89, 0.9)))
        self.assertEqual(reading.dominant_term, "loss_rate")

    def test_one_at_a_time_limitation_is_disclosed(self):
        self.assertIn("do not sum to the total width",
                      " ".join(propagate(_state()).warnings))

    def test_fully_certain_state_has_no_dominant_term(self):
        certain = UncertainState(
            resonance_energy=point(0.9), adaptability=point(0.85),
            diversity=point(0.8), coupling=point(0.9), loss_rate=point(0.1),
        )
        self.assertIsNone(propagate(certain).dominant_term)


class EfficiencyIntervalTests(unittest.TestCase):
    def test_efficiency_interval_is_reported_when_cost_is_known(self):
        reading = propagate(_state(energy_cost=Interval(40.0, 60.0)))
        self.assertIsNotNone(reading.efficiency_interval)

    def test_absent_cost_gives_no_efficiency(self):
        self.assertIsNone(propagate(_state()).efficiency_interval)

    def test_negative_coherence_flips_which_cost_is_worst(self):
        # With M(S) < 0 throughout, the *lowest* cost gives the worst
        # ratio, so naive endpoint pairing would invert the bounds.
        state = _state(
            resonance_energy=Interval(0.1, 0.2), adaptability=Interval(0.1, 0.2),
            diversity=Interval(0.1, 0.2), coupling=Interval(0.2, 0.3),
            loss_rate=Interval(0.5, 0.6), energy_cost=Interval(10.0, 100.0),
        )
        reading = propagate(state)
        self.assertLess(reading.m_interval.hi, 0)
        self.assertLessEqual(reading.efficiency_interval.lo,
                             reading.efficiency_interval.hi)
        self.assertAlmostEqual(reading.efficiency_interval.lo,
                               reading.m_interval.lo / 10.0, places=12)

    def test_zero_cost_is_refused_not_divided_by(self):
        reading = propagate(_state(energy_cost=Interval(0.0, 50.0)))
        self.assertIsNone(reading.efficiency_interval)
        self.assertIn("undefined", " ".join(reading.warnings))


class PercentileTests(unittest.TestCase):
    def test_endpoints(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertAlmostEqual(percentile(values, 0), 1.0)
        self.assertAlmostEqual(percentile(values, 100), 5.0)

    def test_median(self):
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0], 50), 2.0)

    def test_interpolates_between_ranks(self):
        self.assertAlmostEqual(percentile([0.0, 10.0], 25), 2.5)

    def test_single_value(self):
        self.assertAlmostEqual(percentile([7.0], 42), 7.0)

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            percentile([], 50)


class MonteCarloTests(unittest.TestCase):
    def test_samples_never_escape_the_guaranteed_bounds(self):
        state = _state()
        bounds = propagate(state).m_interval
        mc = monte_carlo(state, samples=2000, seed=1)
        for p in mc.percentiles.values():
            self.assertGreaterEqual(p, bounds.lo - 1e-12)
            self.assertLessEqual(p, bounds.hi + 1e-12)

    def test_reading_is_reproducible_for_a_given_seed(self):
        state = _state()
        first = monte_carlo(state, samples=1000, seed=3)
        second = monte_carlo(state, samples=1000, seed=3)
        self.assertEqual(first.median, second.median)
        self.assertEqual(first.probability_negative, second.probability_negative)

    def test_different_seeds_give_different_draws(self):
        state = _state()
        a = monte_carlo(state, samples=1000, seed=1)
        b = monte_carlo(state, samples=1000, seed=2)
        self.assertNotEqual(a.median, b.median)

    def test_strictly_positive_interval_has_zero_negative_mass(self):
        state = _state(
            resonance_energy=Interval(0.85, 0.95), adaptability=Interval(0.85, 0.95),
            diversity=Interval(0.85, 0.95), coupling=Interval(0.9, 0.95),
            loss_rate=Interval(0.01, 0.05),
        )
        self.assertEqual(monte_carlo(state, samples=500, seed=1).probability_negative,
                         0.0)

    def test_signal_probabilities_sum_to_one(self):
        mc = monte_carlo(_state(), samples=1000, seed=1)
        self.assertAlmostEqual(sum(mc.signal_probabilities.values()), 1.0, places=9)

    def test_probability_negative_matches_the_red_mass(self):
        # Without history, M(S) < 0 is exactly the RED condition.
        mc = monte_carlo(_state(), samples=2000, seed=5)
        self.assertAlmostEqual(mc.probability_negative,
                               mc.signal_probabilities.get("RED", 0.0), places=9)

    def test_independence_assumption_is_disclosed(self):
        mc = monte_carlo(_state(), samples=200, seed=1)
        self.assertIn("INDEPENDENTLY", " ".join(mc.warnings))

    def test_distribution_shape_is_disclosed_as_a_choice(self):
        mc = monte_carlo(_state(), samples=200, seed=1)
        self.assertIn("modelling choice", " ".join(mc.warnings))

    def test_mode_switches_the_shape_to_triangular(self):
        state = _state(loss_rate=Interval(0.15, 0.35, mode=0.16))
        mc = monte_carlo(state, samples=2000, seed=1)
        self.assertIn("triangular", " ".join(mc.warnings))
        # Mass concentrated near the low mode raises M(S) relative to uniform.
        uniform = monte_carlo(_state(), samples=2000, seed=1)
        self.assertGreater(mc.median, uniform.median)

    def test_zero_samples_is_rejected(self):
        with self.assertRaises(ValueError):
            monte_carlo(_state(), samples=0)

    def test_returns_the_declared_type(self):
        self.assertIsInstance(monte_carlo(_state(), samples=100), MonteCarloReading)


class FormattingTests(unittest.TestCase):
    def test_format_reports_bounds_and_determination(self):
        text = format_uncertainty(propagate(_state()))
        self.assertIn("M(S) ∈", text)
        self.assertIn("UNDETERMINED", text)
        self.assertIn("UNCERTAINTY CONTRIBUTION", text)

    def test_format_refuses_to_licence_picking_a_verdict(self):
        text = format_uncertainty(propagate(_state()))
        self.assertIn("not a licence to pick one", text)


if __name__ == "__main__":
    unittest.main()
