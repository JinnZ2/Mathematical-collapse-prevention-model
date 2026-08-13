"""Falsifiable tests for src.measurement.validation_timeline_audit."""

import unittest

from src.measurement.validation_timeline_audit import (
    DEFAULT_BASELINE_VALIDATION_YEARS,
    UNKNOWN_DOMAIN_FLOOR_YEARS,
    ValidationTimelineRecord,
    accelerated_validation_window,
    audit_timeline,
    baseline_validation_window,
    gap_analysis,
)


def _record(**overrides):
    defaults = dict(
        forecast_id="f",
        domain="labor_displacement_forecast",
        forecast_publication_date="2022-06-15",
        forecast_horizon_years=3.0,
        earliest_outcome_data_date="2023-06-01",
        full_outcome_data_date="2024-06-01",
        institution_validation_check_date=None,
        institution_still_claims_uncertainty=False,
        human_equivalent_research_years_invested=0.0,
        ai_speedup_factor_assumed=100.0,
    )
    defaults.update(overrides)
    return ValidationTimelineRecord(**defaults)


class BaselineWindowTests(unittest.TestCase):
    def test_known_domain_uses_default(self):
        result = baseline_validation_window(_record())
        self.assertEqual(
            result["baseline_years"],
            DEFAULT_BASELINE_VALIDATION_YEARS["labor_displacement_forecast"],
        )

    def test_unknown_domain_falls_back_to_horizon(self):
        result = baseline_validation_window(_record(
            domain="unmapped_domain",
            forecast_horizon_years=6.0,
        ))
        self.assertEqual(result["baseline_years"], 6.0)

    def test_unknown_domain_floors_at_three_years(self):
        # Short-horizon forecasts in unmapped domains still get a 3-year floor
        result = baseline_validation_window(_record(
            domain="unmapped_domain",
            forecast_horizon_years=1.0,
        ))
        self.assertEqual(result["baseline_years"], UNKNOWN_DOMAIN_FLOOR_YEARS)

    def test_completion_date_lands_after_publication(self):
        result = baseline_validation_window(_record())
        self.assertGreater(
            result["expected_traditional_validation_complete"],
            result["publication_date"],
        )


class AcceleratedWindowTests(unittest.TestCase):
    def test_speedup_compresses_window(self):
        slow = accelerated_validation_window(_record(ai_speedup_factor_assumed=1.0))
        fast = accelerated_validation_window(_record(ai_speedup_factor_assumed=100.0))
        self.assertGreater(slow["accelerated_years"], fast["accelerated_years"])

    def test_speedup_floors_at_one(self):
        # AI cannot make validation slower than traditional science
        result = accelerated_validation_window(_record(ai_speedup_factor_assumed=0.5))
        self.assertEqual(result["speedup_factor"], 1.0)
        self.assertEqual(result["accelerated_years"], result["baseline_years"])

    def test_accelerated_years_equals_baseline_over_speedup(self):
        result = accelerated_validation_window(_record(ai_speedup_factor_assumed=4.0))
        self.assertAlmostEqual(
            result["accelerated_years"],
            result["baseline_years"] / 4.0,
            places=3,
        )


class GapAnalysisTests(unittest.TestCase):
    def test_full_ground_truth_flag_when_reference_past_full_gt(self):
        result = gap_analysis(_record(), reference_date="2026-05-05")
        self.assertIn("FULL_GROUND_TRUTH_AVAILABLE", result["flags"])

    def test_no_full_ground_truth_flag_before_full_gt_date(self):
        result = gap_analysis(_record(), reference_date="2024-01-01")
        self.assertNotIn("FULL_GROUND_TRUTH_AVAILABLE", result["flags"])

    def test_institutional_avoidance_when_uncertainty_claimed_with_gt(self):
        result = gap_analysis(
            _record(institution_still_claims_uncertainty=True),
            reference_date="2026-05-05",
        )
        self.assertIn(
            "INSTITUTION_INVOKES_UNCERTAINTY_DESPITE_GROUND_TRUTH",
            result["flags"],
        )
        self.assertEqual(result["verdict"], "INSTITUTIONAL_AVOIDANCE_DETECTED")

    def test_uncertainty_claim_before_ground_truth_does_not_flag_avoidance(self):
        # If ground truth is not yet in, claiming uncertainty is legitimate
        result = gap_analysis(
            _record(institution_still_claims_uncertainty=True),
            reference_date="2024-01-01",
        )
        self.assertNotIn(
            "INSTITUTION_INVOKES_UNCERTAINTY_DESPITE_GROUND_TRUTH",
            result["flags"],
        )

    def test_overdue_when_no_check_past_accel_deadline(self):
        result = gap_analysis(
            _record(institution_validation_check_date=None),
            reference_date="2026-05-05",
        )
        self.assertIn(
            "NO_VALIDATION_CHECK_PERFORMED_PAST_DEADLINE", result["flags"]
        )
        self.assertEqual(result["verdict"], "VALIDATION_OVERDUE")

    def test_avoidance_takes_precedence_over_overdue(self):
        # When both apply, avoidance is the more severe verdict and should win
        result = gap_analysis(
            _record(
                institution_still_claims_uncertainty=True,
                institution_validation_check_date=None,
            ),
            reference_date="2026-05-05",
        )
        self.assertEqual(result["verdict"], "INSTITUTIONAL_AVOIDANCE_DETECTED")
        self.assertIn(
            "NO_VALIDATION_CHECK_PERFORMED_PAST_DEADLINE", result["flags"]
        )

    def test_acceptable_when_check_recorded_and_no_avoidance(self):
        result = gap_analysis(
            _record(
                institution_validation_check_date="2024-07-01",
                institution_still_claims_uncertainty=False,
            ),
            reference_date="2026-05-05",
        )
        self.assertEqual(result["verdict"], "ACCEPTABLE")
        self.assertNotIn(
            "NO_VALIDATION_CHECK_PERFORMED_PAST_DEADLINE", result["flags"]
        )

    def test_years_since_full_ground_truth_is_negative_before_full_gt(self):
        # Descriptive, not bounded — readers can see that GT has not arrived
        result = gap_analysis(_record(), reference_date="2023-06-01")
        self.assertLess(result["years_since_full_ground_truth"], 0)


class AuditTimelineTests(unittest.TestCase):
    def test_combined_report_has_all_three_layers(self):
        report = audit_timeline(_record(), reference_date="2026-05-05")
        self.assertEqual(set(report.keys()),
                         {"forecast_id", "baseline", "accelerated", "gap"})

    def test_demo_scenario_flags_avoidance(self):
        # The module's own demo case: McKinsey 2022 labor displacement forecast,
        # full ground truth in 2024, institution still claims uncertainty in 2026
        record = _record(
            forecast_id="mck_2022_labor",
            institution_still_claims_uncertainty=True,
            human_equivalent_research_years_invested=520.0,
        )
        report = audit_timeline(record, reference_date="2026-05-05")
        self.assertEqual(
            report["gap"]["verdict"], "INSTITUTIONAL_AVOIDANCE_DETECTED"
        )


if __name__ == "__main__":
    unittest.main()
