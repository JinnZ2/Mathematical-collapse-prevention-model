"""Falsifiable tests for src.measurement.ai_forecast_audit."""

import unittest

from src.measurement.ai_forecast_audit import (
    ComputeBurden,
    ForecastRecord,
    GPU_HOURS_PER_HUMAN_YEAR,
    GroundTruthRecord,
    HUMAN_LABOR_HOURS_PER_YEAR,
    INVESTMENT_RATIO_FAILURE_THRESHOLD,
    aggregate_audit,
    compute_forecast_error,
    compute_human_equivalent_years,
    compute_to_accuracy_ratio,
    systematic_bias_detection,
)


def _forecast(target, predicted, confidence=80.0, title="t", inst="Bank"):
    return ForecastRecord(
        source_institution=inst,
        forecast_title=title,
        forecast_date="2022-01-01",
        horizon_years=3.0,
        target_variable=target,
        predicted_value=predicted,
        predicted_confidence_pct=confidence,
    )


def _truth(target, actual):
    return GroundTruthRecord(
        source="public",
        target_variable=target,
        actual_value=actual,
        measurement_date="2026-01-01",
    )


class ForecastErrorTests(unittest.TestCase):
    def test_exact_forecast_is_100_percent_accurate(self):
        err = compute_forecast_error(_forecast("x", 5.0), _truth("x", 5.0))
        self.assertEqual(err["accuracy_pct"], 100.0)
        self.assertEqual(err["direction"], "EXACT")
        self.assertEqual(err["absolute_error"], 0.0)

    def test_underestimate_direction(self):
        err = compute_forecast_error(_forecast("x", 300000.0), _truth("x", 450000.0))
        self.assertEqual(err["direction"], "UNDERESTIMATED")
        self.assertGreater(err["absolute_error"], 0)

    def test_overestimate_direction(self):
        err = compute_forecast_error(_forecast("x", 5.0), _truth("x", 2.0))
        self.assertEqual(err["direction"], "OVERESTIMATED")
        self.assertLess(err["absolute_error"], 0)

    def test_accuracy_floors_at_zero(self):
        # A wildly wrong forecast must not produce negative "accuracy"
        err = compute_forecast_error(_forecast("x", 1000.0), _truth("x", 1.0))
        self.assertGreaterEqual(err["accuracy_pct"], 0.0)

    def test_variable_mismatch_raises(self):
        with self.assertRaises(ValueError):
            compute_forecast_error(_forecast("a", 1.0), _truth("b", 1.0))

    def test_confidence_inflation_is_surfaced(self):
        # Claimed 90% confidence on a forecast that is only 50% accurate
        err = compute_forecast_error(
            _forecast("x", 2.0, confidence=90.0), _truth("x", 4.0)
        )
        self.assertEqual(err["claimed_confidence_pct"], 90.0)
        self.assertEqual(err["accuracy_pct"], 50.0)
        self.assertEqual(err["confidence_minus_accuracy_pct"], 40.0)


class SystematicBiasTests(unittest.TestCase):
    def test_no_data_returns_no_data_verdict(self):
        self.assertEqual(systematic_bias_detection([])["verdict"], "NO_DATA")

    def test_unanimous_underestimation_is_systematic(self):
        records = [{"direction": "UNDERESTIMATED",
                    "accuracy_pct": 50.0,
                    "claimed_confidence_pct": 90.0} for _ in range(5)]
        result = systematic_bias_detection(records)
        self.assertEqual(result["verdict"], "SYSTEMATIC_UNDERESTIMATION")
        self.assertEqual(result["pct_underestimated"], 100.0)

    def test_unanimous_overestimation_is_systematic(self):
        records = [{"direction": "OVERESTIMATED",
                    "accuracy_pct": 30.0,
                    "claimed_confidence_pct": 85.0} for _ in range(4)]
        self.assertEqual(
            systematic_bias_detection(records)["verdict"],
            "SYSTEMATIC_OVERESTIMATION",
        )

    def test_balanced_errors_yield_no_clear_bias(self):
        records = (
            [{"direction": "UNDERESTIMATED",
              "accuracy_pct": 60.0,
              "claimed_confidence_pct": 80.0}] * 3
            + [{"direction": "OVERESTIMATED",
                "accuracy_pct": 60.0,
                "claimed_confidence_pct": 80.0}] * 3
        )
        self.assertEqual(
            systematic_bias_detection(records)["verdict"],
            "MIXED_NO_CLEAR_BIAS",
        )

    def test_mostly_exact_yields_mostly_accurate(self):
        records = (
            [{"direction": "EXACT",
              "accuracy_pct": 100.0,
              "claimed_confidence_pct": 95.0}] * 4
            + [{"direction": "UNDERESTIMATED",
                "accuracy_pct": 70.0,
                "claimed_confidence_pct": 95.0}]
        )
        self.assertEqual(
            systematic_bias_detection(records)["verdict"],
            "MOSTLY_ACCURATE",
        )

    def test_confidence_inflation_is_aggregate_gap(self):
        records = [{"direction": "UNDERESTIMATED",
                    "accuracy_pct": 40.0,
                    "claimed_confidence_pct": 90.0} for _ in range(3)]
        result = systematic_bias_detection(records)
        self.assertEqual(result["confidence_inflation_pct"], 50.0)


class HumanEquivalentTests(unittest.TestCase):
    def test_missing_fields_contribute_zero(self):
        self.assertEqual(
            compute_human_equivalent_years(ComputeBurden(forecast_id="x")),
            0.0,
        )

    def test_gpu_hours_convert_via_constant(self):
        burden = ComputeBurden(
            forecast_id="x", gpu_hours=GPU_HOURS_PER_HUMAN_YEAR * 2
        )
        self.assertAlmostEqual(compute_human_equivalent_years(burden), 2.0)

    def test_labor_hours_convert_via_constant(self):
        burden = ComputeBurden(
            forecast_id="x",
            institution_labor_hours=HUMAN_LABOR_HOURS_PER_YEAR * 3,
        )
        self.assertAlmostEqual(compute_human_equivalent_years(burden), 3.0)

    def test_signals_sum(self):
        burden = ComputeBurden(
            forecast_id="x",
            gpu_hours=GPU_HOURS_PER_HUMAN_YEAR,
            human_researcher_years=4.0,
            institution_labor_hours=HUMAN_LABOR_HOURS_PER_YEAR,
        )
        self.assertAlmostEqual(compute_human_equivalent_years(burden), 6.0)


class ComputeToAccuracyTests(unittest.TestCase):
    def test_zero_accuracy_yields_infinite_ratio(self):
        burden = ComputeBurden(forecast_id="x", human_researcher_years=5.0)
        ratio = compute_to_accuracy_ratio(burden, {"accuracy_pct": 0.0})
        self.assertEqual(ratio["human_years_per_accuracy_pct_point"], float("inf"))
        self.assertEqual(ratio["verdict"], "INVESTMENT_TO_ACCURACY_RATIO_FAILED")

    def test_high_accuracy_low_burden_is_acceptable(self):
        burden = ComputeBurden(forecast_id="x", human_researcher_years=1.0)
        ratio = compute_to_accuracy_ratio(burden, {"accuracy_pct": 95.0})
        self.assertLess(
            ratio["human_years_per_accuracy_pct_point"],
            INVESTMENT_RATIO_FAILURE_THRESHOLD,
        )
        self.assertEqual(ratio["verdict"], "INVESTMENT_TO_ACCURACY_RATIO_ACCEPTABLE")

    def test_high_burden_low_accuracy_fails(self):
        burden = ComputeBurden(forecast_id="x", human_researcher_years=200.0)
        ratio = compute_to_accuracy_ratio(burden, {"accuracy_pct": 10.0})
        self.assertGreater(
            ratio["human_years_per_accuracy_pct_point"],
            INVESTMENT_RATIO_FAILURE_THRESHOLD,
        )
        self.assertEqual(ratio["verdict"], "INVESTMENT_TO_ACCURACY_RATIO_FAILED")


class AggregateAuditTests(unittest.TestCase):
    def _build(self):
        forecasts = [
            _forecast("a", 100.0, title="f_a"),
            _forecast("b", 5.0, title="f_b"),
            _forecast("c", 1.0, title="f_c"),
        ]
        truths = {
            "a": _truth("a", 200.0),   # underestimate
            "b": _truth("b", 10.0),    # underestimate
            "c": _truth("c", 2.0),     # underestimate
        }
        burdens = {
            "f_a": ComputeBurden(forecast_id="a", human_researcher_years=2.0),
            "f_b": ComputeBurden(forecast_id="b", human_researcher_years=3.0),
            # f_c deliberately omitted to confirm missing-burden handling
        }
        return forecasts, truths, burdens

    def test_unanimous_underestimation_triggers_failure_verdict(self):
        forecasts, truths, burdens = self._build()
        report = aggregate_audit(forecasts, truths, burdens)
        self.assertEqual(report["n_forecasts_audited"], 3)
        self.assertEqual(
            report["systematic_bias"]["verdict"], "SYSTEMATIC_UNDERESTIMATION"
        )
        self.assertEqual(
            report["summary_verdict"], "INSTITUTIONAL_FORECAST_FAILURE_DEMONSTRATED"
        )

    def test_burden_only_counted_when_supplied(self):
        forecasts, truths, burdens = self._build()
        report = aggregate_audit(forecasts, truths, burdens)
        self.assertEqual(len(report["per_forecast_compute_to_accuracy"]), 2)
        self.assertAlmostEqual(report["total_human_equivalent_years_burned"], 5.0)

    def test_forecasts_without_ground_truth_are_skipped(self):
        forecasts, truths, burdens = self._build()
        forecasts.append(_forecast("missing_target", 1.0, title="f_x"))
        report = aggregate_audit(forecasts, truths, burdens)
        self.assertEqual(report["n_forecasts_audited"], 3)


if __name__ == "__main__":
    unittest.main()
