"""Manager agent: verdicts computed by code, report checked, one revision."""
import json
import unittest

from agent.manager import DEFAULT_QUESTION, Escalated, check_report, ManagerDraft, \
    project_facts, write_report
from tests.fixtures import TODAY
from tests.scripted import ScriptedLLM
from tests.test_controller import SOURCES, atlas_state

MEMBERS = ["hugo", "ines", "lea", "marc", "sarah"]


def draft(milestone_evidence=("TSK-001",), members=MEMBERS, extra_ids=()):
    return json.dumps({
        "answer": "Le lancement du 10 novembre est à risque.",
        "deadlines": [{"milestone": "MS-LAUNCH", "explanation": "TSK-001 en retard",
                       "evidence": list(milestone_evidence)}],
        "members": [{"member": m, "summary": "..."} for m in members],
        "recommendations": [], "evidence": ["DEC-004", *extra_ids]})


class FactsTest(unittest.TestCase):
    def test_launch_is_at_risk_with_its_reasons(self):
        facts = project_facts(atlas_state(), [], TODAY)
        [launch] = facts.milestones
        self.assertEqual((launch.date, launch.decision, launch.on_track),
                         ("2026-11-10", "DEC-004", False))
        for id in ("TSK-001", "TCK-QA-012", "TSK-003", "DEC-005"):
            self.assertIn(id, launch.evidence)

    def test_disputed_date_has_no_date_and_names_both_decisions(self):
        dec7 = SOURCES["decisions"][3].model_copy(update={
            "id": "DEC-007", "value": "2026-11-17", "author": "marc", "supersedes": None})
        facts = project_facts(atlas_state(SOURCES["decisions"] + [dec7]), [], TODAY)
        [launch] = facts.milestones
        self.assertIsNone(launch.date)
        self.assertIn("DEC-007", launch.evidence)
        self.assertEqual(facts.conflicts, {"atlas-launch/launch_date": ["DEC-004", "DEC-007"]})

    def test_escalation_sources_can_be_cited(self):
        esc = Escalated(proposal="PROP-MSG-008-1", source="messages/MSG-008", to="lea",
                        reason="sarah may not approve")
        self.assertIn("MSG-008", project_facts(atlas_state(), [esc], TODAY).known_ids())


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.facts = project_facts(atlas_state(), [], TODAY)

    def test_complete_report_passes_without_revision(self):
        llm = ScriptedLLM([draft()])
        report = write_report(llm, DEFAULT_QUESTION, self.facts)
        self.assertEqual(len(llm.calls), 1)
        self.assertFalse(report.control.revised)
        [deadline] = report.deadlines
        self.assertEqual((deadline.on_track, deadline.date), (False, "2026-11-10"))

    def test_check_finds_missing_members_and_invented_ids(self):
        problems = check_report(ManagerDraft.model_validate_json(
            draft(members=["hugo"], extra_ids=["DEC-999"])), self.facts)
        self.assertTrue(any("member ines" in p for p in problems))
        self.assertTrue(any("DEC-999" in p for p in problems))

    def test_one_revision_then_the_code_completes(self):
        bad = draft(milestone_evidence=(), members=["hugo"], extra_ids=["DEC-999"])
        llm = ScriptedLLM([bad, bad])
        report = write_report(llm, DEFAULT_QUESTION, self.facts)
        self.assertEqual(len(llm.calls), 2)  # no third call
        self.assertIn("The code check found", llm.calls[1].user)
        self.assertTrue(report.control.revised and report.control.completed_by_code)
        self.assertEqual(sorted(m.member for m in report.members), MEMBERS)
        self.assertNotIn("DEC-999", report.evidence)

    def test_the_model_cannot_change_a_verdict(self):
        reply = json.loads(draft())
        reply["deadlines"][0]["on_track"] = True
        report = write_report(ScriptedLLM([json.dumps(reply)]), DEFAULT_QUESTION, self.facts)
        self.assertFalse(report.deadlines[0].on_track)


if __name__ == "__main__":
    unittest.main()
