"""The synthetic Atlas corpus loads, is consistent and holds the use case's traps."""
import json
import unittest
from datetime import date

from agent.decisions import conflicts, in_force
from agent.progress import classify
from agent.sources import ROOT, SAMPLE_DIR, SOURCES, load_all, parse_records
from evaluation.expected import load_expected

TODAY = date(2026, 10, 27)
SCENARIOS_DIR = ROOT / "data" / "scenarios"


def overlay(name):
    payload = json.loads((SCENARIOS_DIR / name).read_text(encoding="utf-8"))
    return parse_records(payload["source"], payload)


class CorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_all()
        cls.ids = {name: {getattr(r, "id", None) or getattr(r, "member", None) for r in records}
                   for name, records in cls.data.items()}

    def test_every_file_is_declared_synthetic(self):
        for path in [*SAMPLE_DIR.glob("*.json"), *SCENARIOS_DIR.glob("*.json"),
                     ROOT / "data" / "expected" / "scenarios.json"]:
            with self.subTest(path=path.name):
                self.assertIs(json.loads(path.read_text(encoding="utf-8"))["synthetic"], True)

    def test_one_file_per_source_with_unique_ids(self):
        self.assertEqual({p.stem for p in SAMPLE_DIR.glob("*.json")}, set(SOURCES))
        for name, records in self.data.items():
            with self.subTest(source=name):
                self.assertTrue(records)
                self.assertEqual(len(self.ids[name]), len(records))

    def test_references_resolve(self):
        tasks, members = self.ids["tasks"], self.ids["roles"]
        decisions = self.ids["decisions"]
        for task in self.data["tasks"]:
            self.assertIn(task.member, members)
            self.assertLessEqual(task.start, task.due)
            self.assertTrue(set(task.depends_on) <= tasks, task.id)
        for milestone in self.data["milestones"]:
            self.assertTrue(set(milestone.depends_on) <= tasks)
        for report in self.data["reports"]:
            self.assertIn(report.task_id, tasks)
            self.assertTrue(set(report.blockers) <= self.ids["tickets"])
        for ticket in self.data["tickets"]:
            self.assertTrue(set(ticket.blocks) <= tasks)
            self.assertIn(ticket.related_task, tasks | {None})
        for decision in self.data["decisions"]:
            self.assertIn(decision.author, members)
            self.assertIn(decision.supersedes, decisions | {None})
        for message in self.data["messages"]:
            self.assertIn(message.author, members)
            self.assertIn(message.reply_to, self.ids["messages"] | {None})

    def test_register_gives_10_november_and_sso_in_v2(self):
        rules = in_force(self.data["decisions"])
        self.assertEqual(rules[("atlas-launch", "launch_date")].id, "DEC-004")
        self.assertEqual(rules[("atlas-launch", "sso_release")].value, "v2")
        self.assertEqual(conflicts(self.data["decisions"]), [])

    def test_authority_comes_from_the_role_table(self):
        roles = {r.member: r for r in self.data["roles"]}
        self.assertTrue(roles["lea"].may_approve("atlas-launch", "launch_date"))
        self.assertTrue(roles["marc"].may_approve("atlas-launch", "launch_date"))
        self.assertFalse(roles["sarah"].may_approve("atlas-launch", "launch_date"))
        self.assertFalse(roles["nora"].may_approve("atlas-launch", "launch_date"))

    def test_traps_are_present(self):
        messages = {m.id: m for m in self.data["messages"]}
        self.assertIn("3 novembre", messages["MSG-008"].text)            # old date copied
        self.assertEqual(messages["MSG-009"].project, "helios")          # S4
        tickets = {t.id: t for t in self.data["tickets"]}
        self.assertTrue(tickets["TCK-QA-012"].blocking)                  # QA blocker
        self.assertEqual(tickets["TCK-QA-012"].status, "open")
        brief = {d.id: d for d in self.data["documents"]}["DOC-003"]
        self.assertIn("Tout est prêt", brief.text)                       # sales draft
        lessons = {l.id for p in self.data["past_projects"] for l in p.lessons}
        self.assertIn("LES-ORION-1", lessons)                            # S9

    def test_progress_classification_finds_the_late_and_obsolete_work(self):
        result = classify(self.data["tasks"], self.data["reports"],
                          self.data["decisions"], TODAY)
        late = {f.task_id for f in result.findings if f.case == "late"}
        obsolete = {(f.member, f.decision_id) for f in result.findings if f.case == "obsolete"}
        self.assertEqual(late, {"TSK-001"})
        self.assertEqual(obsolete, {("sarah", "DEC-004"), ("sarah", "DEC-005")})
        self.assertIn(["hugo", "ines"], [m.participants for m in result.meetings])

    def test_scenario_overlays(self):
        s2 = self.data["decisions"] + overlay("s2-decisions.json")
        self.assertEqual(in_force(s2)[("atlas-launch", "launch_date")].value, "2026-11-12")
        s3 = self.data["decisions"] + overlay("s3-decisions.json")
        self.assertNotIn(("atlas-launch", "launch_date"), in_force(s3))
        self.assertEqual({d.id for d in conflicts(s3)[0].decisions}, {"DEC-004", "DEC-007"})


class ExpectedTest(unittest.TestCase):
    def test_expected_results_load_and_cite_known_records(self):
        scenarios = load_expected()
        self.assertEqual(sorted(scenarios), [f"S{i}" for i in range(1, 10)])
        data = load_all()
        known = {getattr(r, "id", None) for records in data.values() for r in records}
        known |= {l.id for p in data["past_projects"] for l in p.lessons}
        known |= {d.id for name in ("s2-decisions.json", "s3-decisions.json")
                  for d in overlay(name)}
        for scenario in scenarios.values():
            cited = set(scenario.open_blockers) | set(scenario.late_tasks)
            cited |= set(scenario.lessons_recalled)
            cited |= {i.decision for i in scenario.in_force}
            cited |= {n.record for n in scenario.not_applied}
            cited |= {d for c in scenario.decision_conflicts for d in c.decisions}
            cited |= {e for m in scenario.meetings for e in m.evidence}
            cited |= {e for x in scenario.escalations for e in x.evidence}
            cited |= {e for c in scenario.member_conflicts for e in c.evidence}
            cited |= {d for s in scenario.stale_claims for d in s.contradicted_by}
            with self.subTest(scenario=scenario.id):
                self.assertEqual(cited - known, set())


if __name__ == "__main__":
    unittest.main()
