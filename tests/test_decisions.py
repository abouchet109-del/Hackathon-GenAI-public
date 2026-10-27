"""Which decision is in force: applicable decisions, conflicts, replacements."""
import unittest

from pydantic import ValidationError

from atlas.decisions import Decision, conflicts, in_force
from tests.fixtures import decision


class DecisionRules(unittest.TestCase):
    def test_replacement_wins_over_the_old_decision(self):
        old = decision("D1", "launch_date", "2026-11-03", day=10)
        new = decision("D2", "launch_date", "2026-11-10", supersedes="D1")
        rules = in_force([old, new])
        self.assertEqual(rules[("atlas-launch", "launch_date")].id, "D2")

    def test_proposal_is_never_in_force(self):
        approved = decision("D1", "launch_date", "2026-11-10")
        proposal = decision("P1", "launch_date", "2026-11-12", status="proposal")
        rules = in_force([approved, proposal])
        self.assertEqual(rules[("atlas-launch", "launch_date")].value, "2026-11-10")

    def test_proposal_does_not_replace_anything(self):
        approved = decision("D1", "launch_date", "2026-11-10")
        proposal = decision("P1", "launch_date", "2026-11-12",
                            status="proposal", supersedes="D1")
        self.assertIn(("atlas-launch", "launch_date"), in_force([approved, proposal]))

    def test_two_incompatible_decisions_are_a_conflict_not_last_wins(self):
        a = decision("D1", "launch_date", "2026-11-10", day=20)
        b = decision("D2", "launch_date", "2026-11-12", day=25)
        found = conflicts([a, b])
        self.assertEqual(len(found), 1)
        self.assertEqual({d.id for d in found[0].decisions}, {"D1", "D2"})
        self.assertNotIn(("atlas-launch", "launch_date"), in_force([a, b]))

    def test_same_value_twice_is_not_a_conflict(self):
        a = decision("D1", "scope", "csv")
        b = decision("D2", "scope", "csv")
        self.assertEqual(conflicts([a, b]), [])

    def test_confidence_must_be_between_0_and_1(self):
        data = decision("D1", "scope", "csv").model_dump() | {"confidence": 2}
        with self.assertRaises(ValidationError):
            Decision.model_validate(data)


if __name__ == "__main__":
    unittest.main()
