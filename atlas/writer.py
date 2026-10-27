"""State writer and notification (task 13, brick 1).

The single writer of the project state: it is the only caller of
StateStore.commit(). It applies what the controller let through, one source
record per write, then notifies the members affected by each new decision in
force (atlas/alerts.py) and records that decision in H-MEM with its
provenance (atlas/hmem.py).
"""
from pydantic import BaseModel

from atlas.alerts import Alert
from atlas.state import Change, Fact


class WriteOutcome(BaseModel):
    version: int            # state version after the write
    changed: bool           # False when the write brought nothing new (S5)
    decisions: list[str] = []
    facts: list[str] = []
    alerts: list[Alert] = []
    memories: list[str] = []  # H-MEM memory ids written


def fact_from(proposal):
    return Fact(id=proposal.id, subject=proposal.subject, attribute=proposal.attribute,
                value=proposal.value, info_type=proposal.info_type, author=proposal.author,
                stated_at=proposal.stated_at, evidence=proposal.evidence)


def change_for(refs, results, summary=""):
    """The Change a set of controller verdicts brings.

    accepted  - the decision (status set by the controller) or a fact
    escalated - a register decision in conflict is recorded too, so the
                conflict is visible and neither value applies (rule 3)
    revision and ignored write nothing but the source ref.
    """
    decisions, facts = [], []
    for result, proposal in results:
        if result.decision is not None and result.verdict in ("accepted", "escalated"):
            decisions.append(result.decision)
        elif result.verdict == "accepted" and proposal.kind != "no_change":
            facts.append(fact_from(proposal))
    return Change(refs=list(refs), decisions=decisions, facts=facts, summary=summary)


class StateWriter:
    def __init__(self, store, inbox, memory=None):
        self.store = store
        self.inbox = inbox
        self.memory = memory  # atlas.hmem.HMem, or None to skip the memory

    def ingest_records(self, records, refs, summary=""):
        """Structured sources (roles, tasks, tickets...) upserted by id."""
        version = self.store.commit(Change(refs=list(refs), records=records, summary=summary))
        return WriteOutcome(version=version or self.store.load().version,
                            changed=version is not None)

    def write(self, refs, results, summary=""):
        """Apply the controller's verdicts for one source (or one batch)."""
        change = change_for(refs, results, summary)
        version = self.store.commit(change)
        state = self.store.load()
        outcome = WriteOutcome(version=state.version, changed=version is not None,
                               decisions=[d.id for d in change.decisions],
                               facts=[f.id for f in change.facts])
        if version is None:
            return outcome
        in_force = {d.id for d in state.in_force().values()}
        evidence = {r.proposal_id: [f"{e.table}/{e.record_id}" for e in p.evidence]
                    for r, p in results}
        for result, _ in results:
            decision = result.decision
            if result.verdict != "accepted" or decision is None:
                continue
            # Every validated decision goes to the memory, a replaced one too,
            # so the trust ledger can say why the date moved; only a decision
            # still in force after the write is worth an alert.
            if decision.id in in_force:
                outcome.alerts += self.inbox.notify(decision, state.tasks, state.reports)
            if self.memory is not None:
                memory, _ = self.memory.record_decision(decision, state.project,
                                                        evidence[result.proposal_id])
                outcome.memories.append(memory.id)
        return outcome
