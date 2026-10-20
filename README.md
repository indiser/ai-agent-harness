# 🤖 AI Agent Harness

> A progressive, hands-on build of an LLM-powered agent — from a bare chat loop to a fully async, MCP-integrated, memory-persistent personal assistant.

---

## 🧠 What Is This?

This project is a **step-by-step construction of an AI agent** using the OpenAI-compatible API (via [OpenRouter](https://openrouter.ai)), built in Python. Each version (`v0` → `v4`) layers in a new capability, making the evolution of the agent architecture explicit and traceable.

---

## 🗺️ Architecture Evolution

```
v0  ──▶  Bare chat loop (stateless, no tools)
v1  ──▶  + Tool calling: list_files, read_file  (single-pass)
v2  ──▶  + write_file  +  agentic loop (multi-turn tool use)
v3  ──▶  + Async  +  MCP servers (time, fetch)
v4  ──▶  + Persistent memory  +  path sandboxing  +  multi-turn conversation history
```

---

## 📁 Project Structure

```
AI AGENT HARNESS/
├── v0.py              # Stateless chat REPL
├── v1.py              # Single-pass tool calling (read-only FS)
├── v2.py              # Agentic loop + file write
├── v3.py              # Async + MCP integration
├── v4.py              # Full agent: memory, sandboxing, multi-turn
├── workspace/         # Agent's sandboxed file system
│   ├── combined.txt
│   ├── hello.txt
│   └── word.txt
├── memory.md          # Persistent user memory (append-only)
├── pyproject.toml
├── requirements.txt
└── .env               # API keys (not committed)
```

---

## 🔬 Version Breakdown

### `v0.py` — Minimal Chat Loop
The foundation. A synchronous REPL that sends a user message to the LLM and prints the response. No tools, no state, no memory.

```
User ──▶ LLM ──▶ Response
```

---

### `v1.py` — Tool Calling (Read-Only, Single-Pass)
Introduces the OpenAI function-calling protocol. The agent can inspect the `workspace/` directory and read files — but only makes **one round of tool calls** before returning.

**Tools:** `list_files`, `read_file`

```
User ──▶ LLM ──▶ [tool call?] ──▶ execute ──▶ LLM ──▶ Response
```

---

### `v2.py` — Agentic Loop + File Write
Upgrades the tool loop to be **iterative**: the agent keeps calling tools until it decides it's done. Adds `write_file` so the agent can produce persistent output.

**Tools:** `list_files`, `read_file`, `write_file`

```
User ──▶ LLM ──▶ [tool calls]* ──▶ LLM ──▶ Response
                    ↑_______________|
```

---

### `v3.py` — Async + MCP Servers
Rewrites the agent as **fully async** (`asyncio` + `AsyncOpenAI`). Connects to external **Model Context Protocol (MCP)** servers over stdio, dynamically registering their tools at startup alongside local tools.

**MCP Servers:** `mcp-server-time`, `mcp-server-fetch`  
**Local Tools:** `list_files`, `read_file`, `write_file`

```
                    ┌─ LOCAL_TOOLS (FS)
User ──▶ LLM ──▶ ──┤
                    └─ MCP_TOOLS (time, fetch, ...)
```

---

### `v4.py` — Full Agent: Memory + Sandboxing + Multi-Turn
The complete agent. Adds:

- **Persistent memory** — `save_memory` appends facts to `memory.md`; loaded into the system prompt at startup so the agent remembers across sessions
- **Path sandboxing** — `safe_path()` resolves and validates all file paths stay inside `workspace/`, preventing directory traversal
- **Multi-turn conversation history** — the full message list is threaded through the session, giving the agent conversational context

```
memory.md ──▶ SYSTEM_PROMPT
                    │
User ──▶ messages[] ──▶ LLM ──▶ [tool calls]* ──▶ LLM ──▶ Response
              ↑___________________________________|
```

---

## ⚙️ Setup

**Prerequisites:** Python ≥ 3.11, [`uv`](https://github.com/astral-sh/uv) (recommended)

```bash
# Install dependencies
uv sync
# or
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENROUTER_API_KEY=<your_openrouter_api_key>
AI_MODEL=<model_id>   # e.g. openai/gpt-4o-mini
```

---

## 🚀 Running

```bash
# Start from the simplest version
python v0.py

# Run the full agent
python v4.py
```

For `v3` and `v4`, `uvx` must be available on your PATH (used to spin up MCP servers):

```bash
pip install uv   # provides uvx
```

---

## 🛠️ Tool Reference

| Tool | Versions | Description |
|---|---|---|
| `list_files` | v1 → v4 | Lists all files in `workspace/` |
| `read_file` | v1 → v4 | Reads a file from `workspace/` |
| `write_file` | v2 → v4 | Writes/overwrites a file in `workspace/` |
| `save_memory` | v4 | Appends a persistent fact to `memory.md` |
| `get_current_time` | v3, v4 | MCP: current time via `mcp-server-time` |
| `fetch` | v3, v4 | MCP: HTTP fetch via `mcp-server-fetch` |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `openai` | OpenAI-compatible API client (sync + async) |
| `mcp` | Model Context Protocol client |
| `python-dotenv` | `.env` loading |
| `pydantic` | Data validation |
| `asyncio` | Async runtime |

---

## 🔐 Security Notes

- `v4.py` introduces `safe_path()` to sandbox all file access within `workspace/` — path traversal attempts (e.g. `../../etc/passwd`) raise a `ValueError`
- API keys are loaded from `.env` and never hardcoded
- `.env` is excluded from version control via `.gitignore`
