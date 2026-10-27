"""Start the Steward MCP server over stdio like Claude Desktop or Cursor would, list its tools and call two.
Run: python scripts/mcp_smoke.py"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def _text(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


async def main() -> int:
    sys.path.insert(0, str(ROOT))
    from app.steward import Steward
    Steward(space="mcp-smoke").reset()  # start from the seeded company memory every time
    env = {**os.environ, "STEWARD_SPACE": "mcp-smoke", "OSEF_MEMBER": "Karim Diallo", "OSEF_AI_TOOL": "Cursor"}
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "run.py"), "mcp"], env=env, cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = sorted(t.name for t in (await session.list_tools()).tools)
            print("tools:", tools)
            brief = json.loads(_text(await session.call_tool("project_brief", {})))
            print("topics in memory:", sorted(brief["topics"]))
            res = json.loads(_text(await session.call_tool(
                "remember", {"content": "The web dashboard is built in React with Vite.", "kind": "decision",
                             "topic": "tech_stack"})))
            print("remember ->", res["decision"], res["citations"])
            hits = json.loads(_text(await session.call_tool("recall", {"query": "price per user", "topic": "pricing"})))
            hits = hits["memories"]
            print("recall pricing ->", [h["content"] for h in hits][:1])
            ctx = json.loads(_text(await session.call_tool("my_context", {"task": "which backend framework do we use?"})))
            print("my_context ->", ctx["approx_tokens"], "tokens, topics", ctx["task_topics"])
            obs = json.loads(_text(await session.call_tool("observe", {
                "excerpt": "I told Martin Plomberie the price is 19 EUR per user per month."})))
            print("observe ->", [(o["decision"], o["topic"]) for o in obs["outcomes"]])
            resources = [str(r.uri) for r in (await session.list_resources()).resources]
            prompts = [p.name for p in (await session.list_prompts()).prompts]
            print("resources:", resources, "prompts:", prompts)
            SPEC_V2 = ["onboard", "observe", "remember", "my_context", "whats_new", "clarifications",
                       "answer_clarification", "recall", "why", "project_brief", "my_contributions",
                       "escalations", "resolve_escalation"]
            COORDINATION = ["my_tasks", "report_progress", "my_alerts"]
            missing = [t for t in SPEC_V2 + COORDINATION if t not in tools]
            print(f"spec v2 tools: {len(SPEC_V2) - len([t for t in SPEC_V2 if t in missing])}/13, coordination: "
                  f"{len(COORDINATION) - len([t for t in COORDINATION if t in missing])}/3, missing: {missing or 'none'}")
            clar = json.loads(_text(await session.call_tool("clarifications", {})))
            print("clarifications ->", len(clar["clarifications"]), "waiting for Karim")
            ok = not missing and len(clar["clarifications"]) >= 1
            ok = ok and obs["outcomes"] and obs["outcomes"][0]["decision"] == "clarify" and "osef://watchlist" in resources
            print("PASS" if ok and res["decision"] == "store" else "FAIL")
            return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
