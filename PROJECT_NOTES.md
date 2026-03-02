# Hackathon Support Agent — Project Notes

## Resume Item

**Hackathon Support Agent** — AI-Powered Q&A Bot for Live Events

*Full version (pick 1–2 bullets that fit your resume):*

- Built an AI agent that served as the primary support channel for a 1,200-participant, 36-hour hackathon (LA Hacks 2025)
- Designed a **ReAct-style orchestration engine** using OpenAI's tool-calling API (gpt-4o-mini) that retrieves answers from three prioritized knowledge sources: Discord FAQ channel (real-time), Google Docs (60s TTL cache), and a static JSON knowledge base
- Implemented **smart escalation routing** — the agent answers when confident, detects distress situations (safety, theft, harassment) to proactively offer human handoff, and forwards unanswerable questions to organizers via Discord webhooks with no disruptive role pings
- Built a **Discord bot client** with incremental pagination caching (500-message cap) so organizer answers posted in an FAQ channel are immediately available to the agent without redeployment
- Deployed as a **Fetch.ai uAgents protocol agent** on the ASI:One network, enabling decentralized agent-to-agent communication
- Engineered production hardening: empty-message filtering to block spam from adversarial agents (zero API cost), casual-message detection to skip expensive retrieval for greetings, and time-aware responses that distinguish past vs. upcoming events
- **Multi-tenant architecture** — a single codebase supports multiple hackathons via YAML config files with secrets injected through environment variables
- Tech stack: Python, OpenAI API, Discord API, Google Docs API, uAgents (Fetch.ai), Docker

*Condensed (1–2 bullet resume version):*

**Hackathon Support Agent** | Python, OpenAI API, Discord API, Fetch.ai uAgents
- Built an AI-powered Q&A agent for a 1,200-participant hackathon using a ReAct-style orchestration engine with OpenAI tool-calling, retrieving answers from three live knowledge sources (Discord FAQ channel, Google Docs, static KB) with smart escalation routing to human organizers via Discord webhooks
- Engineered production hardening for 36-hour continuous operation: adversarial message filtering, incremental Discord message caching (500-msg cap), 60s TTL Google Doc sync, and multi-tenant support via YAML configs — deployed on the Fetch.ai ASI:One decentralized agent network

---

## Trade-Off Decisions

### 1. gpt-4o-mini vs. gpt-4o
- **Chose**: gpt-4o-mini
- **Why**: Latency and cost. Each user question triggers 2–4 API calls (forced retrieve_docs + ReAct loop steps). With 1,200 hackers over 36 hours, gpt-4o would be 10–20x more expensive with noticeably slower responses.
- **Trade-off**: Slightly less nuanced reasoning. Mitigated by forcing retrieve_docs programmatically so the model always has context, reducing its need to "think" about whether to search.

### 2. Forced retrieve_docs vs. letting the model decide
- **Chose**: Always call retrieve_docs programmatically before the ReAct loop
- **Why**: The LLM would sometimes skip retrieval and answer from general knowledge or hallucinate. For a hackathon bot, wrong answers are worse than slow answers.
- **Trade-off**: Every question (except casual greetings) costs one extra API call for retrieval. Acceptable because correctness is critical for event logistics.

### 3. In-memory conversation store vs. persistent storage (Redis/DB)
- **Chose**: In-memory store
- **Why**: Simplicity. The bot runs as a single process and sessions are short-lived (hackers ask 1–3 questions then move on). No need for cross-restart persistence.
- **Trade-off**: If the process crashes, all conversation history is lost. Acceptable because each question is largely self-contained — the bot re-retrieves context every turn anyway.

### 4. TTL cache (Google Doc) vs. webhook/push updates
- **Chose**: 60-second TTL polling cache
- **Why**: Google Docs doesn't offer push notifications for document changes. A short TTL means organizers can update the doc and hackers see changes within a minute — good enough for event logistics.
- **Trade-off**: Up to 60 seconds of stale data. Acceptable because event info doesn't change second-by-second.

### 5. Incremental append-only cache (Discord FAQ) vs. re-fetching all messages
- **Chose**: Incremental append-only with cursor-based pagination
- **Why**: Re-fetching 500 messages on every question would be slow and hit Discord rate limits. The append-only approach only fetches new messages since the last check.
- **Trade-off**: If an organizer edits or deletes an old FAQ message, the cache won't reflect the change. Acceptable because FAQ answers are almost never edited after posting.

### 6. No role pings on escalation vs. pinging organizer roles
- **Chose**: No role pings
- **Why**: During a 36-hour event with 1,200 people, frequent role pings would create notification fatigue. Organizers monitor the FAQ channel actively anyway.
- **Trade-off**: Slightly slower organizer response time. Mitigated by the fact that organizers are physically present at the venue.

### 7. Single-process deployment vs. horizontally scaled service
- **Chose**: Single process
- **Why**: For a single hackathon event, one process handles the load. uAgents framework runs as a single agent instance. Adding load balancing would require a message queue and shared state — over-engineering for a 36-hour event.
- **Trade-off**: Single point of failure. Mitigated with Docker `--restart=always` for auto-recovery.

### 8. Empty message filtering vs. processing everything
- **Chose**: Filter at the application layer
- **Why**: Adversarial agents on the ASI:One network send empty/spam messages. Each one cost 2+ OpenAI API calls before the fix. Filtering saves real money.
- **Trade-off**: If a real user somehow sends an empty message, they get a static greeting instead of being processed. This is actually a better UX.

### 9. Static JSON knowledge base vs. vector database (RAG)
- **Chose**: Static JSON loaded on each call
- **Why**: The hackathon knowledge base is small (~500 lines of JSON). It fits entirely in the LLM's context window. A vector DB adds latency, complexity, and chunking issues for no benefit at this scale.
- **Trade-off**: Won't scale to very large knowledge bases. But for event logistics (schedule, rules, prizes, FAQs), the data is inherently small.

---

## Future Roadmap: Agent-as-a-Service

If we want to turn this into a robust, production-grade service that any hackathon or event can use, here's how to evolve it:

### Tier 1: Core Infrastructure

**1. Persistent Conversation Store (Redis/PostgreSQL)**
- Replace `InMemoryConversationStore` with Redis for session state
- Enables process restarts without losing conversations
- Adds cross-instance session sharing for horizontal scaling
- Interview talking point: "We chose in-memory for the MVP because sessions were short-lived, but for a service, we'd need Redis to survive restarts and support multiple instances"

**2. Horizontal Scaling with Message Queue**
- Put a message queue (RabbitMQ / AWS SQS) between the agent protocol layer and the QA engine
- Multiple QA engine workers consume from the queue
- Handles burst traffic (e.g., 1,200 hackers asking "what's for dinner?" at the same time)
- Interview talking point: "The single-process architecture was a conscious trade-off for a 36-hour event. For a service, we'd decouple ingestion from processing with a queue"

**3. Rate Limiting & Abuse Protection**
- Per-sender rate limits (e.g., 30 messages/hour)
- Blocklist for known bad actors
- Cost ceiling per tenant per day
- Interview talking point: "We discovered adversarial agents on the network spamming our bot. For production, we need rate limiting at the adapter layer before messages hit the expensive LLM pipeline"

**4. Observability & Monitoring**
- Structured logging to a log aggregator (Datadog / CloudWatch)
- Metrics: response latency, API cost per query, cache hit rates, escalation rate
- Alerting: process health, OpenAI API errors, response time degradation
- Dashboard for organizers to see real-time bot usage
- Interview talking point: "During the live event, we had no visibility into whether the bot was degrading. For a service, observability is non-negotiable"

### Tier 2: Intelligence Improvements

**5. Vector Database for RAG**
- Replace context-window stuffing with proper retrieval-augmented generation
- Embed knowledge base chunks, FAQ messages, and Google Doc sections into a vector store (Pinecone / pgvector)
- Retrieve top-k relevant chunks per query instead of dumping everything into the prompt
- Interview talking point: "We fit everything in the context window because the data was small. For larger events or multi-event support, we'd need semantic retrieval to stay within token limits"

**6. Feedback Loop & Active Learning**
- Track which questions get escalated → those are gaps in the knowledge base
- Organizer dashboard to review escalated questions and add answers
- Auto-suggest knowledge base updates based on common escalation patterns
- Interview talking point: "Every escalation is a signal that the knowledge base has a gap. A production system should learn from these"

**7. Multi-LLM Routing**
- Use a fast/cheap model (gpt-4o-mini) for simple factual questions
- Route complex or ambiguous questions to a stronger model (gpt-4o)
- Classification layer decides which model to use based on query complexity
- Interview talking point: "Not all questions need the same model. A router that classifies query complexity can cut costs 50%+ while maintaining quality for hard questions"

### Tier 3: Platform Features

**8. Self-Service Onboarding**
- Web dashboard where organizers upload their knowledge base, connect Discord, paste Google Doc URL
- Auto-generate tenant YAML config
- One-click deploy
- Interview talking point: "Right now onboarding requires manual config files and env vars. For a service, organizers should self-serve in under 5 minutes"

**9. Multi-Channel Support**
- Beyond ASI:One: Slack bot, Discord bot (native, not just webhook), web widget, SMS
- Adapter pattern already supports this — each channel is a thin adapter calling the same QA engine
- Interview talking point: "Our adapter pattern was designed for this. The QA engine has a clean contract — message in, message out. Adding a Slack adapter is ~50 lines of code"

**10. Analytics & Insights**
- What are hackers asking most? (topic clustering)
- When are peak usage times?
- Which knowledge sources answer most questions?
- Post-event report for organizers
- Interview talking point: "The data from 1,200 hackers asking questions over 36 hours is incredibly valuable for organizers to improve future events"

**11. Multi-Language Support**
- Detect message language and respond in kind
- Translate knowledge base on-the-fly or maintain translated versions
- Interview talking point: "International hackathons need multi-language support. The LLM can handle this natively, but the knowledge base would need translation management"

### Architecture Diagram (Future State)

```
                    ┌──────────────┐
                    │  ASI:One     │
                    │  Slack       │──── Adapters ────┐
                    │  Discord     │                  │
                    │  Web Widget  │                  ▼
                    └──────────────┘          ┌──────────────┐
                                              │ Message Queue │
                                              │ (RabbitMQ)    │
                                              └──────┬───────┘
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                             ┌────────────┐  ┌────────────┐  ┌────────────┐
                             │ QA Worker 1│  │ QA Worker 2│  │ QA Worker N│
                             └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
                                   │               │               │
                                   ▼               ▼               ▼
                            ┌─────────────────────────────────────────┐
                            │         Shared Infrastructure           │
                            │  ┌───────────┐  ┌──────────────────┐   │
                            │  │   Redis    │  │  Vector DB       │   │
                            │  │  Sessions  │  │  (Pinecone)      │   │
                            │  └───────────┘  └──────────────────┘   │
                            │  ┌───────────┐  ┌──────────────────┐   │
                            │  │  OpenAI   │  │  Discord/Google  │   │
                            │  │  Router   │  │  Clients         │   │
                            │  └───────────┘  └──────────────────┘   │
                            └─────────────────────────────────────────┘
```

---

## Key Interview Talking Points (Quick Reference)

1. **"Why not RAG/vector DB?"** — Data was small enough to fit in context window. Vector DB adds latency and chunking complexity for no benefit at this scale. Would add it for multi-event support.

2. **"How do you handle hallucination?"** — Forced retrieval before every response. The model can only answer from retrieved context. If nothing relevant is found, it escalates to a human instead of guessing.

3. **"What about concurrent users?"** — Single process handled the event fine. For a service, we'd add a message queue and worker pool. The architecture already separates adapters from the engine.

4. **"How do you handle abuse?"** — Empty message filtering (zero-cost static reply), casual message detection (skip expensive retrieval), and the adapter layer can add rate limiting per sender.

5. **"Why ReAct over a simple chain?"** — ReAct lets the model decide when to escalate vs. answer. A static chain can't handle the judgment call of "is this something I should escalate or can I answer it?" The 3-step cap prevents runaway loops.

6. **"What was the hardest bug?"** — The LLM would sometimes skip retrieval and answer from general knowledge. Fixed by calling retrieve_docs programmatically before the ReAct loop, guaranteeing the model always has real context.

7. **"How do you keep answers fresh?"** — Three-layer freshness: Discord FAQ (real-time via incremental cache), Google Doc (60s TTL), static KB (deploy-time). Organizers can update answers mid-event without touching code.

8. **"What would you do differently?"** — Add observability from day one. During the live event, we had no metrics dashboard. Also, would add a simple web UI for organizers to see what questions are being asked and where the bot is struggling.
