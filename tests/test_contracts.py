import unittest
from datetime import datetime

from pydantic import ValidationError

from atlas.contracts import (CandidateInfo, ControllerResult, DeliverableClaim,
                             Escalation, Evidence, StaleClaim, UpdateProposal,
                             escalation_id)
from tests.fixtures import decision

AT = datetime(2026, 10, 27, 9, 0)
EVIDENCE = [Evidence(table="decisions", record_id="DEC-002",
                     quote="Launch moved to 10 November")]


def candidate(**changes):
    fields = dict(id="CAND-DEC-002-1", project="atlas", subject="atlas-launch",
                  attribute="launch_date", value="2026-11-10", info_type="decision",
                  author="lea", stated_at=AT, evidence=EVIDENCE, confidence=0.9)
    fields.update(changes)
    return CandidateInfo(**fields)


class ContractTest(unittest.TestCase):
    def test_candidate_needs_evidence(self):
        with self.assertRaises(ValidationError):
            candidate(evidence=[])

    def test_unknown_fields_are_refused(self):
        with self.assertRaises(ValidationError):
            candidate(status="approved")  # authority is set by code only

    def test_unknown_info_type_is_refused(self):
        with self.assertRaises(ValidationError):
            candidate(info_type="rumour")

    def test_proposal_allows_one_revision_at_most(self):
        fields = dict(id="PROP-1", candidate_ids=["CAND-DEC-002-1"], kind="supersede",
                      project="atlas", subject="atlas-launch", attribute="launch_date",
                      value="2026-11-10", info_type="decision", author="lea",
                      stated_at=AT, supersedes="DEC-001", rationale="replaces DEC-001",
                      evidence=EVIDENCE, confidence=0.9)
        UpdateProposal(**fields, revision=1)
        with self.assertRaises(ValidationError):
            UpdateProposal(**fields, revision=2)

    def test_controller_result_round_trips_through_json(self):
        result = ControllerResult(
            proposal_id="PROP-1", verdict="accepted",
            checks=[{"name": "author_authorised", "passed": True}],
            decision=decision("DEC-002", "launch_date", "2026-11-10"),
            reason="authorised author, no conflict")
        again = ControllerResult.model_validate_json(result.model_dump_json())
        self.assertEqual(again, result)

    def test_stale_claim_cites_what_contradicts_it(self):
        claim = DeliverableClaim(id="CLM-DOC-005-1", document_id="DOC-005",
                                 subject="atlas-launch", attribute="launch_date",
                                 value="2026-11-03", passage="Launch on 3 November",
                                 confidence=0.8)
        self.assertEqual(claim.as_assumption().attribute, "launch_date")
        with self.assertRaises(ValidationError):
            StaleClaim(claim=claim, expected_value="2026-11-10",
                       contradicted_by=[], reason="")

    def test_escalation_id_is_stable_per_rule_and_subject(self):
        self.assertEqual(escalation_id("R1", "MS-LAUNCH"), escalation_id("R1", "MS-LAUNCH"))
        self.assertNotEqual(escalation_id("R1", "MS-LAUNCH"), escalation_id("R5", "MS-LAUNCH"))
        escalation = Escalation(
            id=escalation_id("R1", "MS-LAUNCH"), rule="R1", level="P1",
            subject="MS-LAUNCH", recipient="marc", expected_action="decide",
            finding="Launch milestone (10/11): CSV acceptance projected to end 13/11",
            gap={"measured": 3, "tolerance": 0}, evidence=["TSK-004", "TCK-QA-012"],
            created_at=AT, updated_at=AT)
        self.assertEqual(escalation.status, "open")
        with self.assertRaises(ValidationError):
            Escalation.model_validate({**escalation.model_dump(), "level": "P0"})


if __name__ == "__main__":
    unittest.main()
