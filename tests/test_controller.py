"""Controller: code checks, one revision at most, escalation to the role table."""
import json
import unittest
from datetime import datetime
from pathlib import Path

from atlas.contracts import Evidence, UpdateProposal
from atlas.controller import arbiter, code_checks, control
from atlas.decisions import Decision
from atlas.sources import load_all
from atlas.state import Change, ProjectState, apply_change
from atlas.updater import from_register
from tests.scripted import ScriptedLLM

ROOT = Path(__file__).resolve().parent.parent
SOURCES = load_all()


def atlas_state(decisions=None):
    return apply_change(ProjectState(project="atlas"), Change(
        records={name: SOURCES[name] for name in ("roles", "tasks", "milestones",
                                                  "tickets", "reports")},
        decisions=SOURCES["decisions"] if decisions is None else decisions))


def proposal(record_id="MSG-099", kind="supersede", info_type="decision", author="lea",
             subject="atlas-launch", attribute="launch_date", value="2026-11-12",
             supersedes="DEC-004", project="atlas", revision=0):
    return UpdateProposal(
        id=f"PROP-{record_id}-1", candidate_ids=[f"CAND-{record_id}-1"], kind=kind,
        project=project, subject=subject, attribute=attribute, value=value,
        info_type=info_type, author=author, stated_at=datetime(2026, 10, 27, 10),
        supersedes=supersedes, rationale="test",
        evidence=[Evidence(table="messages", record_id=record_id, quote="quote")],
        confidence=0.9, revision=revision)


SUPPORTED = '{"supported": true, "reason": "the quote says so"}'


class CodeChecksTest(unittest.TestCase):
    def setUp(self):
        self.state = atlas_state()

    def failed(self, p, ref="messages/MSG-099"):
        return {c.name for c in code_checks(p, self.state, ref) if not c.passed}

    def test_authorised_superseding_decision_passes_the_code(self):
        self.assertEqual(self.failed(proposal()), set())

    def test_authority_comes_from_the_role_table(self):
        self.assertEqual(self.failed(proposal(author="sarah")), {"author_authorised"})

    def test_other_project_fails(self):
        self.assertIn("same_project", self.failed(proposal(project="helios")))

    def test_restating_the_decision_in_force_is_a_duplicate(self):
        p = proposal(kind="new_decision", value="2026-11-10", supersedes=None)
        self.assertIn("not_duplicate", self.failed(p))

    def test_ingested_source_is_a_duplicate(self):
        state = apply_change(self.state, Change(refs=["messages/MSG-099"]))
        failed = {c.name for c in code_checks(proposal(), state, "messages/MSG-099")
                  if not c.passed}
        self.assertEqual(failed, {"not_duplicate"})

    def test_decision_that_does_not_replace_the_one_in_force_conflicts(self):
        p = proposal(kind="new_decision", supersedes=None)
        self.assertEqual(self.failed(p), {"no_conflict"})

    def test_restating_a_replaced_decision_before_its_replacement_is_history(self):
        p = proposal(kind="supersede", value="2026-11-03", supersedes="DEC-004")
        p = p.model_copy(update={"stated_at": datetime(2026, 9, 15, 9, 30)})
        checks = {c.name: c for c in code_checks(p, self.state, "messages/MSG-099")}
        self.assertFalse(checks["not_duplicate"].passed)
        self.assertIn("replaced by DEC-004", checks["not_duplicate"].detail)

    def test_older_statement_cannot_replace_a_newer_decision(self):
        p = proposal(value="2026-11-05").model_copy(
            update={"stated_at": datetime(2026, 10, 1, 9)})
        self.assertEqual(self.failed(p), {"no_conflict"})

    def test_decision_kind_on_a_proposal_is_inconsistent(self):
        self.assertIn("schema", self.failed(proposal(info_type="proposal")))

    def test_no_change_with_another_value_is_inconsistent(self):
        p = proposal(kind="no_change", info_type="work_declaration", author="sarah",
                     value="2026-11-03", supersedes=None)
        self.assertEqual(self.failed(p), {"schema"})

    def test_evidence_must_cite_the_source(self):
        self.assertIn("schema", self.failed(proposal(), ref="messages/MSG-001"))


class ArbiterTest(unittest.TestCase):
    def test_most_specific_person_outside_the_case(self):
        state = atlas_state()
        self.assertEqual(arbiter(state, "atlas-launch", "launch_date", {"sarah"}), "lea")
        self.assertEqual(arbiter(state, "csv-export", "export_formats", {"hugo"}), "lea")

    def test_broadest_authority_when_every_authorised_person_is_involved(self):
        state = atlas_state()
        self.assertEqual(arbiter(state, "atlas-launch", "launch_date", {"lea", "marc"}), "marc")


class ControlTest(unittest.TestCase):
    def setUp(self):
        self.state = atlas_state()

    def test_authorised_decision_is_accepted_with_status_set_by_the_code(self):
        llm = ScriptedLLM([SUPPORTED])
        result = control(llm, proposal(), self.state, "messages/MSG-099", "text")
        self.assertEqual(result.verdict, "accepted")
        self.assertEqual((result.decision.status, result.decision.supersedes),
                         ("approved", "DEC-004"))
        self.assertEqual(result.checks[-1].name, "evidence_supports")

    def test_unauthorised_decision_gets_one_revision_then_escalates(self):
        llm = ScriptedLLM([])
        first = control(llm, proposal(author="sarah"), self.state, "messages/MSG-099")
        self.assertEqual(first.verdict, "revision")
        self.assertIn("role table", first.revision_request)
        second = control(llm, proposal(author="sarah", revision=1), self.state,
                         "messages/MSG-099")
        self.assertEqual((second.verdict, second.escalate_to), ("escalated", "lea"))
        self.assertEqual(llm.calls, [])  # the code decided, no LLM call

    def test_unsupported_evidence_gets_a_revision_then_escalates(self):
        llm = ScriptedLLM(['{"supported": false, "reason": "a suggestion", "fix": "proposal"}'] * 2)
        first = control(llm, proposal(), self.state, "messages/MSG-099", "text")
        self.assertEqual((first.verdict, first.revision_request), ("revision", "proposal"))
        second = control(llm, proposal(revision=1), self.state, "messages/MSG-099", "text")
        self.assertEqual((second.verdict, second.escalate_to), ("escalated", "marc"))  # lea proposed it

    def test_unsupported_fact_after_revision_is_not_written_nor_escalated(self):
        llm = ScriptedLLM(['{"supported": false, "reason": "not said"}'])
        p = proposal(kind="observation", info_type="observation", supersedes=None, revision=1)
        result = control(llm, p, self.state, "messages/MSG-099", "text")
        self.assertEqual((result.verdict, result.decision), ("ignored", None))

    def test_other_project_is_ignored_without_llm(self):
        llm = ScriptedLLM([])
        result = control(llm, proposal(project="helios"), self.state, "messages/MSG-099")
        self.assertEqual(result.verdict, "ignored")

    def test_accepted_fact_has_no_decision(self):
        llm = ScriptedLLM([SUPPORTED])
        p = proposal(kind="observation", info_type="observation", subject="csv-export",
                     attribute="qa_status", value="failing", supersedes=None, author="ines")
        result = control(llm, p, self.state, "messages/MSG-099", "text")
        self.assertEqual((result.verdict, result.decision), ("accepted", None))


class RegisterTest(unittest.TestCase):
    """Register entries are their own evidence: code checks only."""

    def test_conflicting_register_entry_is_recorded_and_escalated_to_marc(self):
        payload = json.loads((ROOT / "data" / "scenarios" / "s3-decisions.json")
                             .read_text(encoding="utf-8"))
        dec7 = Decision.model_validate(payload["records"][0])
        result = control(ScriptedLLM([]), from_register(dec7, "atlas"), atlas_state(),
                         "decisions/DEC-007", record=dec7)
        self.assertEqual((result.verdict, result.escalate_to), ("escalated", "marc"))
        self.assertEqual((result.decision.id, result.decision.status), ("DEC-007", "approved"))

    def test_register_entry_superseding_the_one_in_force_is_accepted(self):
        dec1, dec2, dec3, dec4, _ = SOURCES["decisions"]
        result = control(ScriptedLLM([]), from_register(dec4, "atlas"),
                         atlas_state([dec1, dec2, dec3]), "decisions/DEC-004", record=dec4)
        self.assertEqual(result.verdict, "accepted")


if __name__ == "__main__":
    unittest.main()
