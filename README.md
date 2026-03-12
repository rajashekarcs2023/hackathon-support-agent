# Hackathon Q&A Bot

AI-powered Q&A bot for hackathon participants. Answers questions from three knowledge sources (static KB, live Google Doc, Discord FAQ channel) and can escalate to human organizers when needed.

---

## Features

- **3-source knowledge**: Static JSON KB (baseline) + Google Doc (organizer-updated) + Discord FAQ channel (most recent)
- **Source priority**: FAQ channel > Google Doc > Knowledge Base — newer sources override older ones on conflicts
- **Real-time updates**: Google Doc changes picked up within 60 seconds; FAQ channel messages picked up instantly
- **Smart escalation**: Posts to FAQ channel (no role pings) when the bot can't answer or a hacker needs human help
- **Multi-turn conversations**: Remembers context across messages per session

---

## Architecture

**One entry point.** All handling goes through `QAEngine.answer(message, session_id)` → one reply string.

| Layer | Purpose |
|-------|--------|
| **Adapters** | How messages get in. `run_local.py` = terminal REPL; `agent.py` = uagents chat protocol. |
| **QA engine** | Core. ReAct-style loop (OpenAI tool calls): `retrieve_docs`, `offer_escalation`, `confirm_escalation`. |
| **Clients** | `DiscordBotClient` reads FAQ channel; `GoogleDocClient` fetches hacker guide; `DiscordWebhookClient` sends escalations. |
| **Store** | Per-session state. `ConversationStore` protocol; default is in-memory. Holds history + `pending_escalation`. |
| **Escalation** | `DiscordEscalation` posts to FAQ channel via webhook (no role pings). |

**Flow:** User message → adapter → `engine.answer()` → load context → force `retrieve_docs` (KB + Google Doc + FAQ) → ReAct loop → save context → reply.

---

## Project layout

```
adapters/              # Entry points (local REPL, uagents agent)
qa_engine/             # Engine + store + tools
clients/               # Discord bot, Google Doc, webhook clients
escalation/            # Escalation handlers (Discord webhook)
tenants/               # Per-hackathon YAML configs
hackathonknowledge.json  # Static knowledge base (replaceable per tenant)
```

---

## Setup

### 1. Clone & install

```bash
git clone <repo-url>
cd hackathon-helper
pip install -r requirements.txt
```

### 2. Discord setup

You need **two** Discord integrations — a **webhook** (for sending escalation messages) and a **bot** (for reading FAQ channel messages).

#### Webhook (escalation)

1. Go to your Discord server → **Server Settings → Integrations → Webhooks**
2. Click **New Webhook** → choose the FAQ channel → **Copy Webhook URL**

#### Bot (FAQ channel reader)

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → give it a name → go to **Bot** tab
3. Click **Reset Token** → **Copy** the bot token
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**
5. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Read Messages/View Channels`, `Read Message History`
6. Copy the generated URL → open it in browser → **add bot to your server**

#### Get the FAQ channel ID

1. In Discord, go to **User Settings → Advanced → enable Developer Mode**
2. Right-click the FAQ channel → **Copy Channel ID**

### 3. Google Doc (optional)

1. Create a Google Doc with your hacker guide / FAQ content
2. Click **Share → Anyone with the link → Viewer**
3. Copy the doc ID from the URL: `https://docs.google.com/document/d/{THIS_PART}/edit`

### 4. Environment variables

```bash
cp .env.example .env
```

Fill in your `.env`:

```env
TENANT_CONFIG=tenants/test_tenant.yaml
OPENAI_API_KEY=
AGENT_SEED_PHRASE=
DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
DISCORD_FAQ_CHANNEL_ID=
GOOGLE_DOC_ID=
```

### 5. Knowledge base

Edit `hackathonknowledge.json` with your hackathon's info (schedule, venue, rules, prizes, etc.). Each section includes a `semantic_description` field that helps the AI find the right info.

### 6. Tenant config

Edit `tenants/test_tenant.yaml` to customize the agent name, knowledge base path, and escalation settings.

---

## Usage

**uagents agent (production — connects to ASI:One):**

```bash
python -m adapters.agent
```

**Terminal chatbot (local testing):**

```bash
python -m adapters.run_local
```

---

## How knowledge sources work

| Source | Updated how | Cache | Priority |
|--------|------------|-------|----------|
| **Knowledge Base** (JSON) | Manual edit of file | Read from disk each query | Lowest (baseline) |
| **Google Doc** | Edit the doc in Google Docs | Re-fetched every 60 seconds | Medium |
| **FAQ Channel** | Post messages in Discord | Incremental fetch, in-memory | Highest |

If there's a conflict (e.g., KB says "pizza for lunch" but FAQ channel says "sushi"), the higher-priority source wins.

---

## Tests

```bash
python -m pytest tests/
```

Tests don't need real credentials; webhook calls are mocked.


