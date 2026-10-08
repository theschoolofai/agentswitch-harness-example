# AgentSwitch harness example

A minimal harness that runs on the AgentSwitch server when your team clicks **Our harness → Submit for a run**. Copy the pattern into your own repo.

## What the runner does
1. Checks out the exact commit on the branch you saved in **Our harness**.
2. Runs `install` (internet allowed: PyPI, GitHub).
3. Runs `run` once per instance listed in `instances`, against a **fresh copy** of that instance. Your writes are thrown away. No internet in this step.
4. Reads `results` and shows pass/fail per task and a score in the panel.

One run per team every 3 days. Default limit 20 minutes (max 30).

## 1. `agentswitch-harness.toml` (repo root)
```toml
install = "pip install -r requirements.txt"   # or "uv sync"
run     = "python -m harness.runner"          # your command
results = "results.json"                      # file your run writes (relative path)
instances = ["suryodaya"]                     # and/or "keystone"
timeout_minutes = 20                          # 1-30
```

## 2. Use what the runner gives you (no passwords, no .env, no own keys)
| Variable | Use |
|---|---|
| `AGENTSWITCH_BASE_URL` | the instance: `POST $AGENTSWITCH_BASE_URL/api/mcp` |
| `AGENTSWITCH_TOKEN` | your seat's token: header `Authorization: Bearer $AGENTSWITCH_TOKEN` |
| `AGENTSWITCH_INSTANCE` | `suryodaya` or `keystone` |
| `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` | the platform model, OpenAI-compatible, tool calls supported |

`OpenAI()` from the `openai` package picks up `OPENAI_BASE_URL` and `OPENAI_API_KEY` automatically. LiteLLM and other OpenAI-compatible clients work too; Gemini or Anthropic SDKs do not.

## 3. `results.json`
```json
{"tasks": [{"id": "t1", "title": "What it checks", "passed": true, "score": 1.0, "evidence": "short proof"}],
 "summary": "one line"}
```
`passed` must be `true` or `false`. `score` is optional, 0 to 1. At least 1 task, at most 200. If the file is missing or malformed the run shows **no results** with the reason.

## Run it yourself
Set the same variables (your seat token from your normal login, any OpenAI-compatible model) and run `python -m harness.runner`.
