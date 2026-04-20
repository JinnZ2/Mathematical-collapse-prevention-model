"""Falsifiable tests for src.core.golden_ratio_trust."""

import unittest

from src.core.golden_ratio_trust import PHI, GoldenRatioTrust, TrustState


class InitialChamberTests(unittest.TestCase):
    def test_starts_nascent_with_one_chamber(self):
        grt = GoldenRatioTrust()
        self.assertEqual(len(grt.chambers), 1)
        self.assertEqual(grt.current_state, TrustState.NASCENT)


class ExpansionTests(unittest.TestCase):
    def test_cannot_expand_without_enough_interactions(self):
        grt = GoldenRatioTrust(initial_trust=0.5, trust_threshold=0.3)
        ok, _ = grt.attempt_expand(positive_interactions=1, interaction_quality=0.9)
        self.assertFalse(ok)

    def test_cannot_expand_with_low_quality(self):
        grt = GoldenRatioTrust(initial_trust=0.5, trust_threshold=0.3)
        ok, _ = grt.attempt_expand(positive_interactions=10, interaction_quality=0.3)
        self.assertFalse(ok)

    def test_successful_expansion_follows_phi_ratio(self):
        grt = GoldenRatioTrust(initial_trust=0.5, trust_threshold=0.3)
        ok, _ = grt.attempt_expand(positive_interactions=5, interaction_quality=0.9)
        self.assertTrue(ok)
        self.assertEqual(len(grt.chambers), 2)
        new_chamber = grt.chambers[-1]
        # new chamber trust = foundation * (PHI - 1), foundation = 0.5
        self.assertAlmostEqual(new_chamber.chamber_trust, 0.5 * (PHI - 1), places=9)


class ViolationTests(unittest.TestCase):
    def test_severe_violation_collapses_most_recent_chamber(self):
        grt = GoldenRatioTrust(initial_trust=0.5, trust_threshold=0.3)
        grt.attempt_expand(positive_interactions=5, interaction_quality=0.9)
        self.assertEqual(len(grt.chambers), 2)
        grt.record_violation(severity=0.9)
        self.assertEqual(len(grt.chambers), 1)
        self.assertEqual(grt.current_state, TrustState.DAMAGED)

    def test_moderate_violation_blocks_expansion(self):
        grt = GoldenRatioTrust(initial_trust=0.5, trust_threshold=0.3)
        grt.attempt_expand(positive_interactions=5, interaction_quality=0.9)
        grt.record_violation(severity=0.5)
        self.assertFalse(grt.chambers[-1].can_expand)

    def test_repair_requires_more_than_initial_build(self):
        grt = GoldenRatioTrust(initial_trust=0.5, trust_threshold=0.3)
        grt.attempt_expand(positive_interactions=5, interaction_quality=0.9)
        grt.record_violation(severity=0.5)
        # 3 interactions was enough to build; must not be enough to repair
        ok, _ = grt.repair_trust(repair_interactions=3, repair_quality=0.9)
        self.assertFalse(ok)
        ok, _ = grt.repair_trust(repair_interactions=5, repair_quality=0.9)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
