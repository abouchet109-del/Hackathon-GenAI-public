"""A scripted LLM client for the agents' tests: same call_json() as
agent.structured.LLMClient, answers taken from a list, calls recorded."""
from types import SimpleNamespace


class ScriptedLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def call_json(self, agent, action, system, user, schema):
        self.calls.append(SimpleNamespace(agent=agent, action=action, system=system, user=user))
        if not self.replies:
            raise AssertionError(f"unexpected LLM call: {agent}/{action}")
        text = self.replies.pop(0)
        return schema.model_validate_json(text), SimpleNamespace(text=text, model="scripted")
