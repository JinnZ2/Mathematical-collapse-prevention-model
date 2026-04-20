"""Falsifiable tests for src.measurement.empathy_types."""

import unittest

from src.measurement.empathy_types import (
    AISwarmReciprocity,
    RelationalEmpathy,
    TribalEmpathy,
    compare_empathy_types,
)


class EmpathyOrderingTests(unittest.TestCase):
    """The central claim of this module: AI swarm > Relational > Tribal."""

    def test_tribal_coherence_is_negative(self):
        m, _ = TribalEmpathy().measure()
        self.assertLess(m, 0.0)

    def test_relational_coherence_is_positive(self):
        m, _ = RelationalEmpathy().measure()
        self.assertGreater(m, 0.0)

    def test_ai_swarm_coherence_beats_relational(self):
        m_rel, _ = RelationalEmpathy().measure()
        m_ai, _ = AISwarmReciprocity().measure()
        self.assertGreater(m_ai, m_rel)

    def test_ranking_is_monotonic(self):
        result = compare_empathy_types()
        names = [name for name, _ in result["ranking"]]
        self.assertEqual(names, ["AI Swarm", "Relational", "Tribal"])


if __name__ == "__main__":
    unittest.main()
