"""Falsifiable tests for src.measurement.multi_model_peer_review."""

import unittest

from src.measurement.multi_model_peer_review import (
    GroundTruthPoint,
    ModelPrediction,
    accuracy_vs_ground_truth,
    convergence_metrics,
    divergence_flags,
    peer_review,
)


def _pred(model_id, value, confidence=80.0):
    return ModelPrediction(
        model_id=model_id,
        training_corpus_label="corpus",
        architecture_class="arch",
        predicted_value=value,
        stated_confidence_pct=confidence,
        prediction_date="2022-06-01",
    )


def _gt(actual):
    return GroundTruthPoint(
        target_variable="target",
        actual_value=actual,
        measurement_source="public",
        measurement_date="2026-01-15",
    )


class ConvergenceTests(unittest.TestCase):
    def test_single_model_is_insufficient(self):
        result = convergence_metrics([_pred("a", 100.0)])
        self.assertEqual(result["verdict"], "INSUFFICIENT_MODELS")

    def test_identical_predictions_strong_convergence(self):
        preds = [_pred(f"m{i}", 100.0) for i in range(4)]
        result = convergence_metrics(preds)
        self.assertEqual(result["verdict"], "STRONG_CONVERGENCE")
        self.assertEqual(result["coefficient_of_variation"], 0.0)
        self.assertEqual(result["spread"], 0.0)

    def test_wide_spread_is_divergent(self):
        # CV well above 0.30
        preds = [_pred("a", 10.0), _pred("b", 100.0), _pred("c", 1000.0)]
        self.assertEqual(
            convergence_metrics(preds)["verdict"], "DIVERGENT_NO_CONSENSUS"
        )

    def test_demo_scenario_is_moderate(self):
        # 300k / 320k / 380k ⇒ cv ≈ 0.125, between strong and moderate threshold
        preds = [_pred("a", 300000.0), _pred("b", 320000.0), _pred("c", 380000.0)]
        self.assertEqual(
            convergence_metrics(preds)["verdict"], "MODERATE_CONVERGENCE"
        )


class AccuracyTests(unittest.TestCase):
    def test_accuracy_floors_at_zero(self):
        result = accuracy_vs_ground_truth([_pred("a", 1000.0)], _gt(1.0))
        self.assertEqual(result[0]["accuracy_pct"], 0.0)

    def test_results_sorted_most_accurate_first(self):
        preds = [_pred("far", 200.0), _pred("close", 105.0), _pred("mid", 130.0)]
        result = accuracy_vs_ground_truth(preds, _gt(100.0))
        accuracies = [r["accuracy_pct"] for r in result]
        self.assertEqual(accuracies, sorted(accuracies, reverse=True))
        self.assertEqual(result[0]["model_id"], "close")

    def test_confidence_inflation_surfaced(self):
        # 90% claimed confidence on a 50%-accurate prediction
        result = accuracy_vs_ground_truth(
            [_pred("a", 2.0, confidence=90.0)], _gt(4.0)
        )
        self.assertEqual(result[0]["accuracy_pct"], 50.0)
        self.assertEqual(result[0]["confidence_minus_accuracy_pct"], 40.0)


class DivergenceFlagTests(unittest.TestCase):
    def test_under_three_models_returns_empty(self):
        # IQR is not meaningful below 3 observations
        self.assertEqual(divergence_flags([_pred("a", 1.0), _pred("b", 1000.0)]), [])

    def test_clustered_panel_with_clear_high_outlier(self):
        preds = [
            _pred("a", 100.0),
            _pred("b", 102.0),
            _pred("c", 101.0),
            _pred("d", 99.0),
            _pred("e", 100.0),
            _pred("rogue", 500.0),
        ]
        flags = divergence_flags(preds)
        rogue = [f for f in flags if f["model_id"] == "rogue"]
        self.assertEqual(len(rogue), 1)
        self.assertEqual(rogue[0]["drift_direction"], "HIGH_OUTLIER")

    def test_clustered_panel_with_clear_low_outlier(self):
        preds = [
            _pred("a", 100.0),
            _pred("b", 102.0),
            _pred("c", 101.0),
            _pred("d", 99.0),
            _pred("e", 100.0),
            _pred("rogue", -200.0),
        ]
        flags = divergence_flags(preds)
        rogue = [f for f in flags if f["model_id"] == "rogue"]
        self.assertEqual(rogue[0]["drift_direction"], "LOW_OUTLIER")

    def test_uniform_panel_has_no_flags(self):
        preds = [_pred(f"m{i}", 100.0) for i in range(5)]
        self.assertEqual(divergence_flags(preds), [])


class PeerReviewVerdictTests(unittest.TestCase):
    def test_strong_consensus_with_accurate_panel_is_validated(self):
        preds = [_pred(f"m{i}", 100.0) for i in range(4)]
        report = peer_review(preds, _gt(100.0))
        self.assertEqual(report["peer_review_verdict"], "CONSENSUS_AND_VALIDATED")

    def test_strong_consensus_far_from_truth_is_falsified(self):
        # All models agree on 100, ground truth is 1000 — accuracy is 0
        preds = [_pred(f"m{i}", 100.0) for i in range(4)]
        report = peer_review(preds, _gt(1000.0))
        self.assertEqual(
            report["peer_review_verdict"],
            "CONSENSUS_BUT_FALSIFIED_BY_GROUND_TRUTH",
        )

    def test_strong_consensus_without_truth_awaits(self):
        preds = [_pred(f"m{i}", 100.0) for i in range(4)]
        report = peer_review(preds, ground_truth=None)
        self.assertEqual(
            report["peer_review_verdict"], "CONSENSUS_AWAITING_GROUND_TRUTH"
        )

    def test_divergent_panel_is_fragmented(self):
        preds = [_pred("a", 10.0), _pred("b", 100.0), _pred("c", 1000.0)]
        report = peer_review(preds, _gt(50.0))
        self.assertEqual(report["peer_review_verdict"], "FRAGMENTED_NO_CONSENSUS")

    def test_moderate_panel_requires_more_models(self):
        preds = [_pred("a", 300000.0), _pred("b", 320000.0), _pred("c", 380000.0)]
        report = peer_review(preds, _gt(450000.0))
        self.assertEqual(
            report["peer_review_verdict"],
            "PARTIAL_CONSENSUS_REQUIRES_MORE_MODELS",
        )


if __name__ == "__main__":
    unittest.main()
