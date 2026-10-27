"""Alert inboxes: who is affected, deposit, pull once."""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.coordination.alerts import AlertInbox, affected_members
from tests.coordination.fixtures import decision, report, task

NEW_DATE = decision("D2", "launch_date", "2026-11-10", supersedes="D1", author="lea")
TASKS = [task("CSV", "hugo", date(2026, 10, 30)),
         task("BRIEF", "sarah", date(2026, 10, 30)),
         task("OTHER", "ines", date(2026, 10, 30), subject="another-project")]


class Alerts(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp(prefix="alerts-test-"))
        self.inbox = AlertInbox("atlas", state_dir=self.state)

    def tearDown(self):
        shutil.rmtree(self.state, ignore_errors=True)

    def test_members_on_the_subject_are_affected_but_not_the_author(self):
        tasks = TASKS + [task("PILOT", "lea", date(2026, 10, 30))]
        self.assertEqual(affected_members(NEW_DATE, tasks, []), ["hugo", "sarah"])

    def test_member_relying_on_the_attribute_is_affected(self):
        reports = [report("marc", "X", 0.5, [("launch_date", "2026-11-03")])]
        self.assertIn("marc", affected_members(NEW_DATE, [], reports))

    def test_other_project_is_not_affected(self):
        self.assertNotIn("ines", affected_members(NEW_DATE, TASKS, []))

    def test_alert_is_delivered_once(self):
        self.inbox.notify(NEW_DATE, TASKS, [])
        first = self.inbox.pending("sarah")
        self.assertEqual(len(first), 1)
        self.assertIn("2026-11-10", first[0].message)
        self.assertEqual(self.inbox.pending("sarah"), [])

    def test_notifying_twice_does_not_duplicate(self):
        self.inbox.notify(NEW_DATE, TASKS, [])
        self.assertEqual(self.inbox.notify(NEW_DATE, TASKS, []), [])
        self.assertEqual(len(self.inbox.pending("hugo")), 1)

    def test_inboxes_survive_a_new_process(self):
        self.inbox.notify(NEW_DATE, TASKS, [])
        reopened = AlertInbox("atlas", state_dir=self.state)
        self.assertEqual(len(reopened.pending("hugo")), 1)


if __name__ == "__main__":
    unittest.main()
