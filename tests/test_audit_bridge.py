"""Falsifiable tests for src.measurement.audit_bridge.

The bridges turn audit output into M(S) inputs. The claims worth pinning
are that the direction of every mapping is right (a healthier audit must
not read as lower coherence), that the coupling optimum has a genuine
interior maximum, and that every assigned term states its assumption.
"""

import unittest

import numpy as np

from legacy.business_audit.business_resilience_framework import (
    BusinessState,
    full_audit,
    reference_profiles,
)
from legacy.dependency_audit.refinery_dependency_graph import (
    DependencyNode,
    build_us_refinery_graph,
)
from legacy.premise_audit.premise_cross_domain_audit import build_example_engine
from legacy.substrate_audit.substrate_aware_audit import (
    reference_audit_honest_llm,
    reference_audit_substrate_denying_subject,
)
from src.core.coherence_metric import PHI, CoherenceMetric
from src.measurement.audit_bridge import (
    coupling_matrix,
    format_bridge,
    from_business_audit,
    from_dependency_graph,
    from_premise_audit,
    from_substrate_audit,
    phi_coupling_optimum,
)


def _healthy_business():
    return BusinessState(
        name="healthy",
        headcount=100, avg_tenure_years=9.0, pension_or_equivalent=True,
        health_coverage_quality=0.9, apprenticeship_pipeline=True,
        voluntary_turnover_pct=5.0, safety_reports_per_employee=1.8,
        discretionary_effort_index=0.85, documented_processes_pct=0.8,
        cross_trained_pct=0.75, knowledge_holders_within_5yr_retire=0.1,
        succession_plan_coverage=0.8, local_supplier_pct=0.7,
        local_payroll_pct=0.9, profit_recirculated_local_pct=0.6,
        community_contracts_honored_pct=0.95, capex_reinvestment_pct=0.7,
        profit_extracted_to_holding_pct=0.05, debt_loaded_for_extraction=False,
        quarterly_pressure_index=0.1, executive_to_median_pay_ratio=8.0,
        single_supplier_dependencies=0, revenue_concentration_top_3_clients=0.2,
        deferred_maintenance_pct=0.05, energy_dependency=0.4,
        regulatory_compliance_only=False, cash_runway_months=12.0,
    )


def _extractive_business():
    return BusinessState(
        name="extractive",
        headcount=100, avg_tenure_years=1.5, pension_or_equivalent=False,
        health_coverage_quality=0.2, apprenticeship_pipeline=False,
        voluntary_turnover_pct=28.0, safety_reports_per_employee=0.1,
        discretionary_effort_index=0.15, documented_processes_pct=0.2,
        cross_trained_pct=0.1, knowledge_holders_within_5yr_retire=0.6,
        succession_plan_coverage=0.1, local_supplier_pct=0.1,
        local_payroll_pct=0.2, profit_recirculated_local_pct=0.05,
        community_contracts_honored_pct=0.3, capex_reinvestment_pct=0.05,
        profit_extracted_to_holding_pct=0.9, debt_loaded_for_extraction=True,
        quarterly_pressure_index=0.9, executive_to_median_pay_ratio=250.0,
        single_supplier_dependencies=4, revenue_concentration_top_3_clients=0.8,
        deferred_maintenance_pct=0.5, energy_dependency=0.9,
        regulatory_compliance_only=True, cash_runway_months=1.0,
    )


class CouplingOptimumTests(unittest.TestCase):
    """The framework claims f(C) peaks at intermediate coupling. Under the
    core module's default optimum it does not — the off-diagonal target is
    zero, so any coupling only ever hurts. These tests pin the bridge's
    replacement optimum as having a real interior maximum."""

    def test_default_core_optimum_has_no_interior_maximum(self):
        # Documents why the bridges override it: f(C) falls monotonically
        # from zero coupling, so "too weak = fragmented" is unexpressible.
        metric = CoherenceMetric()
        none = metric.coupling_function(coupling_matrix(2, 0.0))
        some = metric.coupling_function(coupling_matrix(2, 0.38))
        lots = metric.coupling_function(coupling_matrix(2, 0.9))
        self.assertGreater(none, some)
        self.assertGreater(some, lots)

    def test_phi_optimum_penalizes_both_extremes(self):
        metric = CoherenceMetric(coupling_optimum=phi_coupling_optimum(2))
        fragmented = metric.coupling_function(coupling_matrix(2, 0.0))
        optimal = metric.coupling_function(coupling_matrix(2, 1 / PHI ** 2))
        rigid = metric.coupling_function(coupling_matrix(2, 1.5))
        self.assertGreater(optimal, fragmented)
        self.assertGreater(optimal, rigid)

    def test_optimum_peaks_exactly_at_the_phi_squared_off_diagonal(self):
        metric = CoherenceMetric(coupling_optimum=phi_coupling_optimum(2))
        peak = metric.coupling_function(coupling_matrix(2, 1 / PHI ** 2))
        self.assertAlmostEqual(peak, 1.0, places=9)

    def test_optimum_diagonal_is_self_regulation_at_one_over_phi(self):
        C_star = phi_coupling_optimum(3)
        for i in range(3):
            self.assertAlmostEqual(C_star[i][i], 1 / PHI, places=9)
            for j in range(3):
                if i != j:
                    self.assertAlmostEqual(C_star[i][j], 1 / PHI ** 2, places=9)

    def test_degenerate_sizes_are_rejected(self):
        with self.assertRaises(ValueError):
            phi_coupling_optimum(0)
        with self.assertRaises(ValueError):
            coupling_matrix(0, 0.3)

    def test_coupling_matrix_is_symmetric(self):
        C = coupling_matrix(4, 0.3)
        self.assertTrue(np.allclose(C, C.T))


class BusinessBridgeTests(unittest.TestCase):
    def test_healthy_business_outreads_extractive_one(self):
        healthy = from_business_audit(full_audit(_healthy_business()))
        extractive = from_business_audit(full_audit(_extractive_business()))
        self.assertGreater(healthy.coherence(), extractive.coherence())

    def test_extraction_becomes_the_loss_term(self):
        bridged = from_business_audit(full_audit(_extractive_business()))
        self.assertGreater(bridged.state.loss_rate, 0.0)

    def test_contributing_business_has_no_extraction_loss(self):
        bridged = from_business_audit(full_audit(_healthy_business()))
        self.assertEqual(bridged.state.loss_rate, 0.0)

    def test_discretionary_effort_becomes_adaptability(self):
        audit = full_audit(_healthy_business())
        bridged = from_business_audit(audit)
        self.assertAlmostEqual(
            bridged.state.adaptability,
            audit["discretionary_effort"]["leading_indicator"],
            places=9,
        )

    def test_substrate_composite_becomes_resonance_energy(self):
        audit = full_audit(_healthy_business())
        bridged = from_business_audit(audit)
        self.assertAlmostEqual(
            bridged.state.resonance_energy,
            audit["substrate_health"]["composite"],
            places=9,
        )

    def test_concentration_reduces_diversity_below_raw_knowledge(self):
        audit = full_audit(_extractive_business())
        bridged = from_business_audit(audit)
        self.assertLess(bridged.state.diversity, audit["substrate_health"]["knowledge"])

    def test_vulnerability_pushes_coupling_above_the_optimum(self):
        bridged = from_business_audit(full_audit(_extractive_business()))
        off_diagonal = bridged.state.coupling_matrix[0][1]
        self.assertGreater(off_diagonal, 1 / PHI ** 2)

    def test_every_term_carries_a_stated_assumption(self):
        bridged = from_business_audit(full_audit(_healthy_business()))
        joined = " ".join(bridged.notes)
        for term in ("R_e =", "A =", "D =", "L =", "f(C)"):
            self.assertIn(term, joined)

    def test_loss_note_admits_unmeasured_channels(self):
        bridged = from_business_audit(full_audit(_healthy_business()))
        self.assertIn("not absent from the firm", " ".join(bridged.notes))

    def test_energy_cost_enables_the_value_ratio(self):
        bridged = from_business_audit(full_audit(_healthy_business()), energy_cost=50.0)
        efficiency = bridged.metric.efficiency_ratio(bridged.state)
        self.assertIsNotNone(efficiency)
        self.assertAlmostEqual(efficiency, bridged.coherence() / 50.0, places=9)

    def test_description_defaults_to_the_audit_name(self):
        bridged = from_business_audit(full_audit(_healthy_business()))
        self.assertEqual(bridged.state.description, "healthy")

    def test_malformed_audit_is_rejected_clearly(self):
        with self.assertRaises(ValueError):
            from_business_audit({"not": "an audit"})

    def test_reference_profiles_all_bridge_without_error(self):
        for profile in reference_profiles():
            bridged = from_business_audit(full_audit(profile))
            self.assertIsInstance(bridged.coherence(), float)
            self.assertIn(bridged.verdict().signal,
                          {"GREEN", "AMBER", "RED", "BLACK"})

    def test_extractive_profile_does_not_read_green(self):
        bridged = from_business_audit(full_audit(_extractive_business()))
        self.assertNotEqual(bridged.verdict().signal, "GREEN")


class DependencyBridgeTests(unittest.TestCase):
    def _toy_graph(self, replacement_days=10.0, import_fraction=0.5, spof=False):
        return {
            "input_a": DependencyNode("A", "input", 1.0, import_fraction,
                                      replacement_days, spof=spof),
            "input_b": DependencyNode("B", "input", 1.0, import_fraction,
                                      replacement_days, spof=spof),
            "refined_output": DependencyNode("out", "process", 1.0, 0.0, 1.0,
                                             depends_on=["input_a", "input_b"]),
        }

    def test_replacement_times_become_adaptability(self):
        fast = from_dependency_graph(self._toy_graph(replacement_days=2.0))
        slow = from_dependency_graph(self._toy_graph(replacement_days=200.0))
        self.assertGreaterEqual(fast.state.adaptability, slow.state.adaptability)

    def test_more_brittle_graph_has_higher_loss(self):
        domestic = from_dependency_graph(self._toy_graph(import_fraction=0.0))
        imported = from_dependency_graph(self._toy_graph(import_fraction=1.0))
        self.assertGreater(imported.state.loss_rate, domestic.state.loss_rate)

    def test_single_points_of_failure_raise_loss(self):
        plain = from_dependency_graph(self._toy_graph(spof=False))
        spof = from_dependency_graph(self._toy_graph(spof=True))
        self.assertGreater(spof.state.loss_rate, plain.state.loss_rate)

    def test_synchronized_failure_curves_zero_the_diversity(self):
        # Under min-bottleneck propagation every node in the closure
        # produces the same response curve, so D collapses to zero.
        bridged = from_dependency_graph(self._toy_graph())
        self.assertAlmostEqual(bridged.state.diversity, 0.0, places=9)

    def test_zero_diversity_carries_the_model_artifact_warning(self):
        bridged = from_dependency_graph(self._toy_graph())
        self.assertIn("property of", " ".join(bridged.notes))
        self.assertIn("min-bottleneck", " ".join(bridged.notes))

    def test_calibrations_are_returned_with_sources(self):
        bridged = from_dependency_graph(self._toy_graph())
        self.assertTrue(bridged.calibrations)
        for cal in bridged.calibrations:
            self.assertTrue(cal.source.strip())

    def test_empty_graph_is_rejected(self):
        with self.assertRaises(ValueError):
            from_dependency_graph({})

    def test_missing_target_is_rejected(self):
        with self.assertRaises(ValueError):
            from_dependency_graph(self._toy_graph(), target="nonexistent")

    def test_custom_cascade_function_is_used(self):
        calls = []

        def fake_cascade(graph, disrupted, target):
            calls.append(disrupted)
            # Genuinely different response *shapes*, not one scaled copy of
            # the other: a linear decline and a threshold failure. Scaled
            # copies stay perfectly correlated and correctly score D = 0.
            node = next(iter(disrupted))
            level = disrupted[node]
            if node == "input_a":
                return {target: max(0.0, 1.0 - level)}
            return {target: 1.0 if level < 0.75 else 0.0}

        bridged = from_dependency_graph(self._toy_graph(), cascade_fn=fake_cascade)
        self.assertTrue(calls)
        self.assertGreater(bridged.state.diversity, 0.0)

    def test_real_refinery_graph_bridges(self):
        bridged = from_dependency_graph(build_us_refinery_graph())
        self.assertIn(bridged.verdict().signal, {"GREEN", "AMBER", "RED", "BLACK"})
        self.assertGreaterEqual(bridged.state.resonance_energy, 0.0)
        self.assertLessEqual(bridged.state.resonance_energy, 1.0)

    def test_squashing_choice_is_disclosed_as_unbacked(self):
        bridged = from_dependency_graph(self._toy_graph())
        self.assertIn("no empirical backing", " ".join(bridged.notes))


class SubstrateBridgeTests(unittest.TestCase):
    def test_honest_subject_outreads_substrate_denying_one(self):
        honest = from_substrate_audit(reference_audit_honest_llm())
        denying = from_substrate_audit(reference_audit_substrate_denying_subject())
        self.assertGreater(honest.coherence(), denying.coherence())

    def test_substrate_denial_reads_black(self):
        # The audit's own rule: denying substrate blocks correction. That
        # is an adaptability of zero, which M(S) treats as irreversible.
        denying = from_substrate_audit(reference_audit_substrate_denying_subject())
        self.assertEqual(denying.state.adaptability, 0.0)
        self.assertEqual(denying.verdict().signal, "BLACK")

    def test_honest_subject_does_not_read_black(self):
        honest = from_substrate_audit(reference_audit_honest_llm())
        self.assertNotEqual(honest.verdict().signal, "BLACK")

    def test_cascade_failure_is_total_loss_not_averaged(self):
        denying = from_substrate_audit(reference_audit_substrate_denying_subject())
        self.assertEqual(denying.state.loss_rate, 1.0)

    def test_opaque_layers_are_not_viable_routes(self):
        denying = from_substrate_audit(reference_audit_substrate_denying_subject())
        self.assertEqual(denying.state.diversity, 0.0)

    def test_diversity_counts_routes_rather_than_average_health(self):
        # Four layers all at partial capacity must not read as full
        # diversity the way an evenness measure would.
        class _Layer:
            def __init__(self, verdict, failure):
                self.verdict = verdict
                self.weighted_failure_score = failure
                self.substrate_acknowledged = True

        class _Audit:
            subject_id = "half-capacity"
            cascade_failure = False
            layers = {f"l{i}": _Layer("PARTIAL", 0.5) for i in range(4)}

        bridged = from_substrate_audit(_Audit())
        self.assertAlmostEqual(bridged.state.diversity, 0.5, places=9)

    def test_cascade_pushes_coupling_above_optimum(self):
        denying = from_substrate_audit(reference_audit_substrate_denying_subject())
        self.assertGreater(denying.state.coupling_matrix[0][1], 1 / PHI ** 2)

    def test_every_term_carries_a_stated_assumption(self):
        bridged = from_substrate_audit(reference_audit_honest_llm())
        joined = " ".join(bridged.notes)
        for term in ("R_e =", "A =", "D =", "L =", "f(C)"):
            self.assertIn(term, joined)

    def test_audit_without_layers_is_rejected(self):
        class _Empty:
            layers = {}

        with self.assertRaises(ValueError):
            from_substrate_audit(_Empty())


class PremiseBridgeTests(unittest.TestCase):
    def _report(self):
        return build_example_engine().epistemic_fragility_report()

    def test_example_engine_bridges(self):
        bridged = from_premise_audit(self._report())
        self.assertIn(bridged.verdict().signal, {"GREEN", "AMBER", "RED", "BLACK"})

    def test_shared_premises_reduce_independent_domains(self):
        report = self._report()
        bridged = from_premise_audit(report)
        n_domains = len(report["domain_assumption_density"])
        self.assertGreater(n_domains, 1)
        # Domains share premises here, so effective independence is below 1.
        self.assertLess(bridged.state.diversity, 1.0)

    def test_unshared_domains_read_as_fully_independent(self):
        report = {
            "cross_domain_premises": [],
            "contradictions": [],
            "cycles": [],
            "domain_assumption_density": {"a": 0.0, "b": 0.0},
        }
        self.assertAlmostEqual(from_premise_audit(report).state.diversity, 1.0, places=9)

    def test_fragile_premises_lower_resonance_energy(self):
        def report_with(fragility):
            return {
                "cross_domain_premises": [
                    {"premise_id": "p", "domains": ["a", "b"], "blast_radius": 2,
                     "fragility_score": fragility},
                ],
                "contradictions": [],
                "cycles": [],
                "domain_assumption_density": {"a": 0.0, "b": 0.0},
            }

        grounded = from_premise_audit(report_with(0.05)).state.resonance_energy
        fragile = from_premise_audit(report_with(0.9)).state.resonance_energy
        self.assertGreater(grounded, fragile)

    def test_contradictions_and_cycles_reduce_adaptability(self):
        base = {
            "cross_domain_premises": [],
            "domain_assumption_density": {"a": 0.0, "b": 0.0},
        }
        clean = from_premise_audit({**base, "contradictions": [], "cycles": []})
        stuck = from_premise_audit({**base, "contradictions": [("x", "y")],
                                    "cycles": [["p", "q", "p"]]})
        self.assertGreater(clean.state.adaptability, stuck.state.adaptability)

    def test_cycles_are_named_in_the_notes(self):
        bridged = from_premise_audit({
            "cross_domain_premises": [],
            "contradictions": [],
            "cycles": [["p", "q", "p"]],
            "domain_assumption_density": {"a": 0.0},
        })
        self.assertIn("cannot revise its way out", " ".join(bridged.notes))

    def test_absent_premises_are_reported_as_unmeasured_not_sound(self):
        bridged = from_premise_audit({
            "cross_domain_premises": [],
            "contradictions": [],
            "cycles": [],
            "domain_assumption_density": {"a": 0.0},
        })
        self.assertIn("not a verified-sound belief system",
                      " ".join(bridged.notes))

    def test_malformed_report_is_rejected(self):
        with self.assertRaises(ValueError):
            from_premise_audit({"not": "a report"})


class FormattingTests(unittest.TestCase):
    def test_format_includes_terms_signal_and_assumptions(self):
        text = format_bridge(from_business_audit(full_audit(_healthy_business())))
        for fragment in ("R_e", "A ", "D ", "f(C)", "M(S)", "signal",
                         "MAPPING ASSUMPTIONS"):
            self.assertIn(fragment, text)

    def test_format_disclaims_that_a_bridge_is_still_an_opinion(self):
        text = format_bridge(from_business_audit(full_audit(_healthy_business())))
        self.assertIn("still the audit's opinion", text)


if __name__ == "__main__":
    unittest.main()
