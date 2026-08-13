"""Falsifiable tests for src.measurement.early_warning.

Each test pins a claim the module makes about early-warning signals:
critical slowing down is detectable in a system whose recovery rate
erodes, absent in one whose recovery rate holds, and honest about the
cases where it can say nothing.
"""

import random
import unittest

from src.measurement.early_warning import (
    MIN_POINTS_AR1,
    ar1_surrogates,
    critical_slowing_down,
    kendall_tau,
    lag1_autocorrelation,
    linear_detrend,
    rate_induced_tipping,
    return_time,
    rolling,
    variance,
)


def ar1_series(alpha, n=120, noise=0.1, seed=1):
    """Generate an AR(1) series with fixed coefficient."""
    rng = random.Random(seed)
    out, x = [], 0.0
    for _ in range(n):
        x = alpha * x + rng.gauss(0, noise)
        out.append(x)
    return out


def eroding_series(start=0.10, end=0.95, n=120, noise=0.1, seed=1):
    """AR(1) series whose coefficient climbs — a system losing recovery rate."""
    rng = random.Random(seed)
    out, x = [], 0.0
    for i in range(n):
        alpha = start + (end - start) * (i / (n - 1))
        x = alpha * x + rng.gauss(0, noise)
        out.append(x)
    return out


class AutocorrelationTests(unittest.TestCase):
    def test_high_alpha_series_reads_high(self):
        alpha = lag1_autocorrelation(ar1_series(0.9), detrend=False)
        self.assertIsNotNone(alpha)
        self.assertGreater(alpha, 0.6)

    def test_low_alpha_series_reads_low(self):
        alpha = lag1_autocorrelation(ar1_series(0.1), detrend=False)
        self.assertIsNotNone(alpha)
        self.assertLess(alpha, 0.4)

    def test_slower_recovery_reads_higher_than_faster(self):
        slow = lag1_autocorrelation(ar1_series(0.9, seed=3), detrend=False)
        fast = lag1_autocorrelation(ar1_series(0.2, seed=3), detrend=False)
        self.assertGreater(slow, fast)

    def test_constant_series_has_no_defined_autocorrelation(self):
        self.assertIsNone(lag1_autocorrelation([2.0] * 30))

    def test_short_series_returns_none(self):
        self.assertIsNone(lag1_autocorrelation([1.0, 2.0, 3.0]))
        self.assertEqual(MIN_POINTS_AR1, 5)

    def test_detrending_removes_trend_inflation(self):
        # A pure linear ramp with tiny noise: undetrended AR(1) is inflated
        # by the trend itself, detrended it is not.
        rng = random.Random(5)
        ramp = [0.1 * i + rng.gauss(0, 0.01) for i in range(60)]
        self.assertGreater(lag1_autocorrelation(ramp, detrend=False), 0.9)
        self.assertLess(lag1_autocorrelation(ramp, detrend=True), 0.5)


class DetrendTests(unittest.TestCase):
    def test_linear_ramp_detrends_to_zero(self):
        residuals = linear_detrend([1.0, 2.0, 3.0, 4.0, 5.0])
        for r in residuals:
            self.assertAlmostEqual(r, 0.0, places=9)

    def test_detrend_preserves_length(self):
        series = [3.0, 1.0, 4.0, 1.0, 5.0]
        self.assertEqual(len(linear_detrend(series)), len(series))


class ReturnTimeTests(unittest.TestCase):
    def test_return_time_diverges_as_alpha_approaches_one(self):
        near = return_time(0.99)
        far = return_time(0.5)
        self.assertGreater(near, far)

    def test_alpha_at_or_above_one_has_no_return_time(self):
        self.assertIsNone(return_time(1.0))
        self.assertIsNone(return_time(1.2))

    def test_non_positive_alpha_has_no_return_time(self):
        self.assertIsNone(return_time(0.0))
        self.assertIsNone(return_time(-0.3))

    def test_none_alpha_propagates(self):
        self.assertIsNone(return_time(None))


class KendallTauTests(unittest.TestCase):
    def test_strictly_rising_is_one(self):
        self.assertAlmostEqual(kendall_tau([1.0, 2.0, 3.0, 4.0]), 1.0)

    def test_strictly_falling_is_minus_one(self):
        self.assertAlmostEqual(kendall_tau([4.0, 3.0, 2.0, 1.0]), -1.0)

    def test_flat_series_is_undefined(self):
        self.assertIsNone(kendall_tau([2.0, 2.0, 2.0]))

    def test_short_series_returns_none(self):
        self.assertIsNone(kendall_tau([1.0]))


class VarianceTests(unittest.TestCase):
    def test_single_point_has_no_variance(self):
        self.assertIsNone(variance([1.0]))

    def test_constant_series_has_zero_variance(self):
        self.assertAlmostEqual(variance([3.0, 3.0, 3.0]), 0.0)


class RollingTests(unittest.TestCase):
    def test_window_count(self):
        self.assertEqual(len(rolling(list(range(10)), 4)), 7)

    def test_window_larger_than_series_yields_nothing(self):
        self.assertEqual(rolling([1.0, 2.0], 5), [])


class CriticalSlowingDownTests(unittest.TestCase):
    def test_eroding_system_shows_the_signature(self):
        reading = critical_slowing_down(eroding_series(seed=5))
        self.assertEqual(reading.flag, "CRITICAL_SLOWING_DOWN")
        self.assertGreater(reading.ar1_trend_tau, 0.5)
        self.assertGreater(reading.variance_trend_tau, 0.5)

    def test_stable_system_shows_no_signature(self):
        reading = critical_slowing_down(ar1_series(0.2, seed=0))
        self.assertEqual(reading.flag, "NO_SIGNAL")

    def test_no_signal_output_states_it_is_not_a_safety_guarantee(self):
        reading = critical_slowing_down(ar1_series(0.2, seed=0))
        joined = " ".join(reading.warnings).lower()
        self.assertIn("not evidence", joined)

    def test_partial_signal_also_disclaims_safety(self):
        # A single rising indicator is not a clean bill of health either.
        reading = critical_slowing_down(eroding_series(seed=7))
        self.assertEqual(reading.flag, "PARTIAL_SIGNAL")
        self.assertIn("not evidence of safety", " ".join(reading.warnings).lower())

    def test_short_series_is_insufficient_data_not_a_verdict(self):
        reading = critical_slowing_down([1.0, 2.0, 3.0])
        self.assertEqual(reading.flag, "INSUFFICIENT_DATA")
        self.assertIsNone(reading.lag1_autocorrelation)
        self.assertIn("No statement about system state", " ".join(reading.warnings))

    def test_too_few_windows_is_insufficient_data(self):
        # Long enough for a lag-1 estimate, too short for a trend statistic.
        reading = critical_slowing_down(ar1_series(0.5, n=6, seed=2))
        self.assertEqual(reading.flag, "INSUFFICIENT_DATA")
        self.assertIn("rolling windows", " ".join(reading.warnings))

    def test_near_unit_autocorrelation_is_reported(self):
        # A random walk: alpha ~ 1, perturbations never decay.
        walk = ar1_series(1.0, n=120, seed=4)
        reading = critical_slowing_down(walk)
        self.assertGreater(reading.lag1_autocorrelation, 0.0)
        self.assertGreater(reading.n_windows, 0)

    def test_reading_is_reproducible_from_the_same_series(self):
        # Surrogates are seeded, so the p-values must repeat exactly too.
        series = eroding_series(seed=11)
        first = critical_slowing_down(series)
        second = critical_slowing_down(series)
        self.assertEqual(first.flag, second.flag)
        self.assertEqual(first.ar1_trend_tau, second.ar1_trend_tau)
        self.assertEqual(first.ar1_p_value, second.ar1_p_value)
        self.assertEqual(first.variance_p_value, second.variance_p_value)


class SignificanceTests(unittest.TestCase):
    """The surrogate null is what makes the tau threshold a test.

    Rolling windows overlap, so the indicator series is autocorrelated and
    a bare |tau| >= 0.5 threshold fires on a large share of perfectly
    stationary series. These tests pin the difference.
    """

    # Twelve seeds at the module's default surrogate count. Fewer
    # surrogates would run faster but changes the answer: at 50 the null
    # is under-sampled, p inflates, and detection drops from 75% to 45%.
    SEEDS = range(12)

    def _flags(self, builder, **kwargs):
        return [critical_slowing_down(builder(seed=s), **kwargs).flag
                for s in self.SEEDS]

    def test_surrogate_test_cuts_the_false_alarm_rate(self):
        raw = self._flags(lambda seed: ar1_series(0.2, seed=seed), significance=False)
        tested = self._flags(lambda seed: ar1_series(0.2, seed=seed))
        raw_alarms = sum(1 for f in raw if f != "NO_SIGNAL")
        tested_alarms = sum(1 for f in tested if f != "NO_SIGNAL")
        self.assertLess(tested_alarms, raw_alarms)

    def test_false_alarm_rate_on_stationary_series_is_low(self):
        # Pins the ~8% any-flag / ~0% joint-flag rates documented in the
        # module docstring.
        flags = self._flags(lambda seed: ar1_series(0.2, seed=seed))
        any_flag = sum(1 for f in flags if f != "NO_SIGNAL")
        joint = sum(1 for f in flags if f == "CRITICAL_SLOWING_DOWN")
        self.assertLessEqual(any_flag / len(flags), 0.25)
        self.assertLessEqual(joint / len(flags), 0.10)

    def test_eroding_systems_are_still_mostly_detected(self):
        # Guards against making the test so strict it detects nothing.
        # Pins the ~75% detection rate documented in the module docstring.
        flags = self._flags(lambda seed: eroding_series(seed=seed))
        detected = sum(1 for f in flags
                       if f in ("CRITICAL_SLOWING_DOWN", "PARTIAL_SIGNAL"))
        self.assertGreaterEqual(detected / len(flags), 0.5)

    def test_partial_signal_is_the_common_detection_state(self):
        # The module docstring claims PARTIAL_SIGNAL is the workhorse and
        # CRITICAL_SLOWING_DOWN the rare high-confidence state. If that
        # ever inverts, the docstring is wrong and this test says so.
        flags = self._flags(lambda seed: eroding_series(seed=seed))
        self.assertGreater(
            sum(1 for f in flags if f == "PARTIAL_SIGNAL"),
            sum(1 for f in flags if f == "CRITICAL_SLOWING_DOWN"),
        )

    def test_p_values_are_bounded_and_never_exactly_zero(self):
        # (hits + 1) / (total + 1) — a finite surrogate set cannot support
        # a claim of zero probability.
        reading = critical_slowing_down(eroding_series(seed=5))
        for p in (reading.ar1_p_value, reading.variance_p_value):
            self.assertIsNotNone(p)
            self.assertGreater(p, 0.0)
            self.assertLessEqual(p, 1.0)

    def test_surrogates_match_length_and_are_stationary_by_construction(self):
        series = eroding_series(seed=3)
        surrogates = ar1_surrogates(series, count=5, seed=1)
        self.assertEqual(len(surrogates), 5)
        for s in surrogates:
            self.assertEqual(len(s), len(series))

    def test_flat_series_yields_no_surrogates(self):
        self.assertEqual(ar1_surrogates([1.0] * 40), [])

    def test_significance_disabled_reports_no_p_values(self):
        reading = critical_slowing_down(eroding_series(seed=5), significance=False)
        self.assertIsNone(reading.ar1_p_value)
        self.assertIsNone(reading.variance_p_value)


class RateInducedTippingTests(unittest.TestCase):
    def test_forcing_faster_than_recovery_flags_risk(self):
        forcing = [0.05 * t for t in range(20)]
        reading = rate_induced_tipping(forcing, adaptability=0.03)
        self.assertEqual(reading.flag, "RATE_TIPPING_RISK")

    def test_forcing_slower_than_recovery_is_within_capacity(self):
        forcing = [0.01 * t for t in range(20)]
        reading = rate_induced_tipping(forcing, adaptability=0.5)
        self.assertEqual(reading.flag, "WITHIN_TRACKING_CAPACITY")
        self.assertGreater(reading.margin, 0)

    def test_zero_adaptability_always_flags_risk(self):
        reading = rate_induced_tipping([0.0, 0.0, 0.0], adaptability=0.0)
        self.assertEqual(reading.flag, "RATE_TIPPING_RISK")

    def test_peak_rate_alone_triggers_the_flag(self):
        # Mean rate stays well below A, but one step outruns recovery.
        forcing = [0.001 * t for t in range(40)] + [0.5]
        reading = rate_induced_tipping(forcing, adaptability=0.1)
        self.assertEqual(reading.flag, "RATE_TIPPING_RISK")
        self.assertLess(reading.forcing_rate, 0.1)
        self.assertGreater(reading.peak_forcing_rate, 0.1)

    def test_single_point_forcing_is_insufficient(self):
        reading = rate_induced_tipping([1.0], adaptability=0.5)
        self.assertEqual(reading.flag, "INSUFFICIENT_DATA")
        self.assertIsNone(reading.forcing_rate)


if __name__ == "__main__":
    unittest.main()
