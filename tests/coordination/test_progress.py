"""The four cases of the progress classification."""
import unittest
from datetime import date

from app.coordination.progress import classify
from tests.coordination.fixtures import TODAY, decision, report, task

DECISIONS = [
    decision("D1", "launch_date", "2026-11-03", day=10),
    decision("D2", "launch_date", "2026-11-10", supersedes="D1"),
    decision("D3", "sso", "v2"),
]


def cases(result, member):
    return sorted(f.case for f in result.findings if f.member == member)


class ProgressClassification(unittest.TestCase):
    def test_ok_when_on_track(self):
        result = classify([task("T1", "hugo", date(2026, 10, 30))],
                          [report("hugo", "T1", 0.6)], DECISIONS, TODAY)
        self.assertEqual(cases(result, "hugo"), ["ok"])
        self.assertEqual(result.meetings, [])

    def test_late_when_past_due_and_not_done(self):
        result = classify([task("T1", "hugo", date(2026, 10, 25))],
                          [report("hugo", "T1", 0.7)], DECISIONS, TODAY)
        finding = result.findings[0]
        self.assertEqual(finding.case, "late")
        self.assertIn("70%", finding.reason)

    def test_done_task_past_due_is_not_late(self):
        result = classify([task("T1", "hugo", date(2026, 10, 25))],
                          [report("hugo", "T1", 1.0)], DECISIONS, TODAY)
        self.assertEqual(cases(result, "hugo"), ["ok"])

    def test_no_report_past_due_is_late(self):
        result = classify([task("T1", "hugo", date(2026, 10, 25))], [], DECISIONS, TODAY)
        self.assertEqual(cases(result, "hugo"), ["late"])

    def test_obsolete_when_work_relies_on_a_replaced_value(self):
        result = classify([task("T1", "sarah", date(2026, 10, 30))],
                          [report("sarah", "T1", 0.5, [("launch_date", "2026-11-03")])],
                          DECISIONS, TODAY)
        finding = result.findings[0]
        self.assertEqual(finding.case, "obsolete")
        self.assertEqual(finding.decision_id, "D2")

    def test_latest_report_is_the_one_that_counts(self):
        reports = [report("sarah", "T1", 0.5, [("launch_date", "2026-11-03")], hour=8),
                   report("sarah", "T1", 0.6, [("launch_date", "2026-11-10")], hour=10)]
        result = classify([task("T1", "sarah", date(2026, 10, 30))], reports, DECISIONS, TODAY)
        self.assertEqual(cases(result, "sarah"), ["ok"])

    def test_late_and_obsolete_can_both_apply(self):
        result = classify([task("T1", "sarah", date(2026, 10, 25))],
                          [report("sarah", "T1", 0.5, [("sso", "v1")])], DECISIONS, TODAY)
        self.assertEqual(cases(result, "sarah"), ["late", "obsolete"])

    def test_meeting_when_one_decision_makes_two_members_obsolete(self):
        tasks = [task("T1", "sarah", date(2026, 10, 30)), task("T2", "hugo", date(2026, 10, 30))]
        reports = [report("sarah", "T1", 0.5, [("sso", "v1")]),
                   report("hugo", "T2", 0.5, [("sso", "v1")])]
        result = classify(tasks, reports, DECISIONS, TODAY)
        self.assertEqual(len(result.meetings), 1)
        self.assertEqual(result.meetings[0].participants, ["hugo", "sarah"])
        self.assertEqual(result.meetings[0].evidence, ["D3"])

    def test_meeting_when_a_late_task_blocks_another_member(self):
        tasks = [task("CSV", "hugo", date(2026, 10, 25)),
                 task("BRIEF", "sarah", date(2026, 10, 30), depends_on=["CSV"])]
        reports = [report("hugo", "CSV", 0.7), report("sarah", "BRIEF", 0.4)]
        result = classify(tasks, reports, DECISIONS, TODAY)
        self.assertEqual(len(result.meetings), 1)
        self.assertEqual(result.meetings[0].participants, ["hugo", "sarah"])
        self.assertEqual(result.meetings[0].evidence, ["CSV", "BRIEF"])

    def test_no_meeting_when_the_blocker_is_on_time(self):
        tasks = [task("CSV", "hugo", date(2026, 10, 30)),
                 task("BRIEF", "sarah", date(2026, 10, 31), depends_on=["CSV"])]
        result = classify(tasks, [report("hugo", "CSV", 0.7)], DECISIONS, TODAY)
        self.assertEqual(result.meetings, [])

    def test_disputed_decision_does_not_make_work_obsolete(self):
        disputed = DECISIONS + [decision("D4", "launch_date", "2026-11-12")]
        result = classify([task("T1", "sarah", date(2026, 10, 30))],
                          [report("sarah", "T1", 0.5, [("launch_date", "2026-11-03")])],
                          disputed, TODAY)
        self.assertEqual(cases(result, "sarah"), ["ok"])


if __name__ == "__main__":
    unittest.main()
