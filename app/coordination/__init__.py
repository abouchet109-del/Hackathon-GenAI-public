"""Team coordination: the bridge between Steward's company memory and the team's Atlas modules.

The decision register, the per-member progress classification and the alert inboxes live in `atlas/`
(Adam Semlali, Alexandre Bouchet); `bridge.py` feeds them from H-MEM (decisions in force), Zetaris (tasks)
and each person's AI (progress reports), and is used by app/steward.py and the MCP tools
my_tasks, report_progress and my_alerts.
"""
