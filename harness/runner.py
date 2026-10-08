"""Minimal AgentSwitch harness: MCP checks plus a tiny agent loop on the platform model.

Everything comes from environment variables set by the AgentSwitch runner:
  AGENTSWITCH_BASE_URL, AGENTSWITCH_TOKEN, AGENTSWITCH_INSTANCE
  OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL   (read by the OpenAI SDK / below)
No passwords, no .env, no keys of your own.
"""
import json
import os
import re

import requests
from openai import OpenAI

BASE = os.environ["AGENTSWITCH_BASE_URL"].rstrip("/")
AUTH = {"Authorization": "Bearer " + os.environ["AGENTSWITCH_TOKEN"]}
INSTANCE = os.environ.get("AGENTSWITCH_INSTANCE", "unknown")
MODEL = os.environ.get("OPENAI_MODEL", "agentswitch-default")

tasks = []


def record(task_id, title, passed, evidence):
    tasks.append({"id": f"{INSTANCE}:{task_id}", "title": title,
                  "passed": bool(passed), "score": 1.0 if passed else 0.0,
                  "evidence": str(evidence)[:500]})
    print(f"[{'PASS' if passed else 'FAIL'}] {task_id}: {str(evidence)[:200]}", flush=True)


def mcp(method, params=None, rid=1):
    r = requests.post(f"{BASE}/api/mcp", headers=AUTH, timeout=120,
                      json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
    r.raise_for_status()
    return r.json()


def call_tool(name, arguments):
    body = mcp("tools/call", {"name": name, "arguments": arguments or {}})
    result = body.get("result") or {}
    text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    return text or json.dumps(body)[:2000]


# 1. MCP is reachable with the seat token.
try:
    tools = (mcp("tools/list").get("result") or {}).get("tools") or []
    record("mcp_tools_list", "MCP tools/list works with the seat token", len(tools) > 0, f"{len(tools)} tools")
except Exception as exc:  # noqa: BLE001
    record("mcp_tools_list", "MCP tools/list works with the seat token", False, repr(exc))

# 2. A direct tool call: read our own saved harness link.
expected_url = ""
try:
    text = call_tool("TeamHarness.get_mine", {})
    found = re.search(r"https://github\.com/[\w.-]+/[\w.-]+", text)
    expected_url = found.group(0) if found else ""
    record("mcp_tool_call", "TeamHarness.get_mine returns our saved link", bool(expected_url), text[:300])
except Exception as exc:  # noqa: BLE001
    record("mcp_tool_call", "TeamHarness.get_mine returns our saved link", False, repr(exc))

# 3. A tiny agent loop: the model must use the tool and answer with the link.
client = OpenAI()  # reads OPENAI_BASE_URL and OPENAI_API_KEY
TOOLS = [{"type": "function", "function": {
    "name": "get_my_harness_link",
    "description": "Return the GitHub link this team saved for its agent harness.",
    "parameters": {"type": "object", "properties": {}}}}]
messages = [{"role": "system", "content": "You are a helpful agent. Use tools when needed. Answer briefly."},
            {"role": "user", "content": "What GitHub link did my team save for its harness? Reply with just the URL."}]
answer, used_tool = "", False
try:
    for _ in range(4):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, max_tokens=512)
        msg = reply.choices[0].message
        if msg.tool_calls:
            used_tool = True
            messages.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": call_tool("TeamHarness.get_mine", {})})
            continue
        answer = msg.content or ""
        break
    ok = used_tool and bool(expected_url) and expected_url.rstrip("/") in answer
    record("agent_answers_with_tool", "The agent uses the tool and answers with our link", ok,
           f"used_tool={used_tool} answer={answer[:200]!r}")
except Exception as exc:  # noqa: BLE001
    record("agent_answers_with_tool", "The agent uses the tool and answers with our link", False, repr(exc))

with open("results.json", "w") as fh:
    json.dump({"tasks": tasks,
               "summary": f"{INSTANCE}: {sum(t['passed'] for t in tasks)}/{len(tasks)} checks passed"}, fh, indent=2)
