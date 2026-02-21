# Hackathon Q&A Bot

AI-powered Q&A bot for hackathon participants: answers from a knowledge base and can escalate to human organizers when it can’t answer or when someone needs help.

---

## Architecture

**One entry point.** All handling goes through `QAEngine.answer(message, session_id)` → one reply string. Callers (terminal, uagents, future HTTP) only pass a message and session; they don’t branch or retry.

| Layer | Purpose |
|-------|--------|
| **Adapters** | How messages get in. `run_local.py` = terminal REPL; `agent.py` = uagents chat protocol. Both call the engine and return its reply. |
| **QA engine** | Core. ReAct-style loop (OpenAI tool calls): `retrieve_docs`, `offer_escalation`, `confirm_escalation`. Knowledge from a JSON KB today; designed to be swappable. |
| **Store** | Per-session state. `ConversationStore` protocol (load/save by `session_id`); default is in-memory. Holds history + `pending_escalation` so multi-turn and “offer → confirm” escalation work. |
| **Escalation** | `DiscordWebhookClient` is a helper for when a hackathon chooses Discord for escalation. Escalation is not wired into the engine yet; that’s intentional. |

**Flow:** User message → adapter → `engine.answer()` → load context → ReAct loop (model may call tools) → save context → reply. Session identity is a string (e.g. `"local"` or uagents `sender`); may become UUID later.

**Patterns:** Single facade (engine); pluggable store (protocol); thin adapters; tool-calling for orchestration.

---

## Project layout

```
adapters/          # Entry points (local REPL, uagents agent)
qa_engine/         # Engine + store + tools (retrieve_docs, escalation)
escalation/        # Discord webhook helper (for future escalation wiring)
env.py             # Required env vars + config; require_env() at startup
hackathonknowledge.json   # Current knowledge base (replaceable)
```

See `RFP_HACKATHON_BOT_CONFIGURATION.md` for what hackathon committees provide and how escalation is intended to work.

---

## Setup

1. **Copy env:** `cp .env.example .env` and fill in all required keys (see `env.py`).
2. **Discord (for escalation path):** Server Settings → Integrations → Webhooks → New Webhook → copy URL. Enable Developer Mode, then right-click the role to ping → Copy Role ID. Put both in `.env`.
3. **Install:** `pip install -r requirements.txt`

---

## Usage

**Terminal chatbot:**

```bash
python -m adapters.run_local
```

**uagents agent (chat protocol):**

```bash
python -m adapters.agent
```

**Discord webhook (helper only; e.g. when you wire escalation):**

```python
from escalation.discord import DiscordWebhookClient
client = DiscordWebhookClient(webhook_url="...", role_id="...")
client.send("Something went wrong!")
```

---

## Tests

```bash
python -m pytest tests/
```

Tests don’t need real credentials; webhook calls are mocked.
