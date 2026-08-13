"""
Validation Timeline Audit (2026)

Companion to ai_forecast_audit. Quantifies how long a forecast should
take to validate, given the human-equivalent compute investment behind
it, and flags when an institution invokes "complex systems need more
time" past the threshold where ground truth is already conclusive.

Three layers:

1. Baseline human validation timeline (traditional science speed).
2. AI compute acceleration factor — how much faster validation should
   run given investment.
3. Gap analysis — outcome data available vs. institution still
   claiming uncertainty.

MEASUREMENT, NOT CONTROL
------------------------
This module REPORTS schedule gaps. It does not enforce deadlines,
recommend sanctions, or score institutions for action. Verdicts
describe the gap between investment, ground truth, and stated
position. Readers decide what the gap means.

Standard library only.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional


# =============================================================================
# BASELINE TIMELINES (traditional human-only science)
# =============================================================================

# Conservative defaults. Override per-domain if needed.
DEFAULT_BASELINE_VALIDATION_YEARS: Dict[str, float] = {
    "macroeconomic_forecast": 5.0,            # GDP, employment, wages
    "labor_displacement_forecast": 4.0,       # automation impact
    "inflation_forecast": 2.0,
    "wage_adjustment_forecast": 3.0,
    "monetary_policy_outcome": 3.0,
    "infrastructure_investment_outcome": 7.0,
    "ecological_recovery_forecast": 10.0,
    "policy_intervention_outcome": 4.0,
    "consumer_behavior_forecast": 2.0,
    "financial_stability_forecast": 5.0,
}

DAYS_PER_YEAR = 365.25
UNKNOWN_DOMAIN_FLOOR_YEARS = 3.0


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class ValidationTimelineRecord:
    """Inputs needed to audit a single forecast's validation timeline."""

    forecast_id: str
    domain: str
    forecast_publication_date: str               # ISO
    forecast_horizon_years: float
    earliest_outcome_data_date: str              # when ground truth started arriving
    full_outcome_data_date: str                  # when enough ground truth to validate
    institution_validation_check_date: Optional[str] = None
    institution_still_claims_uncertainty: bool = False
    human_equivalent_research_years_invested: float = 0.0
    ai_speedup_factor_assumed: float = 100.0     # conservative AI acceleration


def _parse(d: str) -> datetime:
    return datetime.fromisoformat(d)


def _years_between(d1: str, d2: str) -> float:
    return (_parse(d2) - _parse(d1)).days / DAYS_PER_YEAR


def _add_years(start: datetime, years: float) -> datetime:
    """Add a fractional number of years using calendar days."""
    return start + timedelta(days=years * DAYS_PER_YEAR)


def _baseline_years_for(record: ValidationTimelineRecord) -> float:
    base = DEFAULT_BASELINE_VALIDATION_YEARS.get(record.domain)
    if base is None:
        base = max(record.forecast_horizon_years, UNKNOWN_DOMAIN_FLOOR_YEARS)
    return base


# =============================================================================
# LAYER 1: BASELINE HUMAN VALIDATION TIMELINE
# =============================================================================


def baseline_validation_window(record: ValidationTimelineRecord) -> Dict:
    """How long should a traditional human-led validation take?

    Returns the expected validation completion date assuming traditional
    science speed for the domain.
    """
    base = _baseline_years_for(record)
    pub = _parse(record.forecast_publication_date)
    expected_complete = _add_years(pub, base)
    return {
        "domain": record.domain,
        "baseline_years": base,
        "publication_date": record.forecast_publication_date,
        "expected_traditional_validation_complete":
            expected_complete.date().isoformat(),
    }


# =============================================================================
# LAYER 2: AI COMPUTE ACCELERATION FACTOR
# =============================================================================


def accelerated_validation_window(record: ValidationTimelineRecord) -> Dict:
    """How compressed should the validation window be under AI acceleration?

    Divides the baseline by the assumed speedup factor (floored at 1.0
    so AI cannot make validation slower than traditional science).
    """
    baseline = _baseline_years_for(record)
    speedup = max(record.ai_speedup_factor_assumed, 1.0)
    accelerated_years = baseline / speedup
    pub = _parse(record.forecast_publication_date)
    expected_complete = _add_years(pub, accelerated_years)
    return {
        "baseline_years": baseline,
        "speedup_factor": speedup,
        "accelerated_years": round(accelerated_years, 3),
        "human_equivalent_research_years_invested":
            record.human_equivalent_research_years_invested,
        "expected_ai_validation_complete":
            expected_complete.date().isoformat(),
    }


# =============================================================================
# LAYER 3: GAP ANALYSIS
# =============================================================================


def gap_analysis(
    record: ValidationTimelineRecord,
    reference_date: Optional[str] = None,
) -> Dict:
    """Compare expected timelines to actual ground-truth availability.

    Flags institutional avoidance when ground truth is in but the
    institution still claims uncertainty, and flags overdue validation
    when no check has been recorded past the AI-accelerated deadline.
    """
    if reference_date is None:
        reference_date = datetime.now().date().isoformat()

    ref = _parse(reference_date)
    full_gt = _parse(record.full_outcome_data_date)

    years_since_publication = _years_between(
        record.forecast_publication_date, reference_date
    )
    years_since_full_gt = _years_between(
        record.full_outcome_data_date, reference_date
    )

    accel = accelerated_validation_window(record)
    baseline = baseline_validation_window(record)
    accel_complete = _parse(accel["expected_ai_validation_complete"])

    flags = []
    verdict = "ACCEPTABLE"

    if ref >= full_gt:
        flags.append("FULL_GROUND_TRUTH_AVAILABLE")
    if ref >= accel_complete:
        flags.append("AI_VALIDATION_WINDOW_EXPIRED")
    if record.institution_still_claims_uncertainty and ref >= full_gt:
        flags.append("INSTITUTION_INVOKES_UNCERTAINTY_DESPITE_GROUND_TRUTH")
        verdict = "INSTITUTIONAL_AVOIDANCE_DETECTED"
    if (record.institution_validation_check_date is None
            and ref >= accel_complete):
        flags.append("NO_VALIDATION_CHECK_PERFORMED_PAST_DEADLINE")
        if verdict == "ACCEPTABLE":
            verdict = "VALIDATION_OVERDUE"

    return {
        "reference_date": reference_date,
        "years_since_publication": round(years_since_publication, 2),
        "years_since_full_ground_truth": round(years_since_full_gt, 2),
        "expected_ai_validation_complete":
            accel["expected_ai_validation_complete"],
        "expected_traditional_validation_complete":
            baseline["expected_traditional_validation_complete"],
        "flags": flags,
        "verdict": verdict,
    }


# =============================================================================
# AGGREGATE REPORT
# =============================================================================


def audit_timeline(
    record: ValidationTimelineRecord,
    reference_date: Optional[str] = None,
) -> Dict:
    """Run all three layers for a single forecast and return a combined report."""
    return {
        "forecast_id": record.forecast_id,
        "baseline": baseline_validation_window(record),
        "accelerated": accelerated_validation_window(record),
        "gap": gap_analysis(record, reference_date),
    }


# =============================================================================
# DEMO
# =============================================================================


if __name__ == "__main__":
    print("VALIDATION TIMELINE AUDIT — Demo")
    print("=" * 60)

    record = ValidationTimelineRecord(
        forecast_id="mck_2022_labor",
        domain="labor_displacement_forecast",
        forecast_publication_date="2022-06-15",
        forecast_horizon_years=3.0,
        earliest_outcome_data_date="2023-06-01",
        full_outcome_data_date="2024-06-01",
        institution_validation_check_date=None,
        institution_still_claims_uncertainty=True,
        human_equivalent_research_years_invested=520.0,
        ai_speedup_factor_assumed=100.0,
    )

    report = audit_timeline(record, reference_date="2026-05-05")

    print(f"Forecast: {report['forecast_id']}")
    print()
    print("Baseline (traditional human-led science):")
    for k, v in report["baseline"].items():
        print(f"  {k}: {v}")
    print()
    print("Accelerated (AI compute equivalence):")
    for k, v in report["accelerated"].items():
        print(f"  {k}: {v}")
    print()
    print("Gap analysis (institution behavior vs. timeline):")
    for k, v in report["gap"].items():
        print(f"  {k}: {v}")
