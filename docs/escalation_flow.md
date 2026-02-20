# Escalation flow: use cases, implementation, interfaces

## 1. Use case flow (when we escalate)

Escalation is **expensive** (pings hackathon committee). We only escalate when **both** conditions hold:

1. **We cannot answer the question** (engine decides it’s out of scope, no confident answer, or error).
2. **The user confirms** they want to escalate (explicit “yes” / “escalate” / button).

So escalation is **never automatic**. The flow is:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. User sends a message                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Engine tries to answer                                                     │
│    - Same as today: LLM + subject scope (hackathon Q&A)                        │
│    - Engine must also decide: “can answer” vs “cannot answer”                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │ CAN answer            │       │ CANNOT answer         │
        │ → Return answer        │       │ → Return explanation  │
        │   (done)               │       │   + offer escalation  │
        └───────────────────────┘       └───────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. User sees: “I couldn’t answer … Would you like me to escalate to the     │
│    committee?” (or similar)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. User sends follow-up message                                              │
│    - “Yes” / “escalate” / “please” → treat as confirmation                   │
│    - Anything else (e.g. new question) → treat as new turn, go to step 1     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │ User CONFIRMS         │       │ User does NOT confirm │
        │ escalation            │       │ (new question / no)   │
        │ → Perform escalation  │       │ → No ping, respond    │
        │   (e.g. Discord ping) │       │   as normal           │
        │ → Tell user “Done”     │       └───────────────────────┘
        └───────────────────────┘
```

**Out of scope / errors**

- **Out of scope:** Question not about subject matter → “cannot answer” + offer escalation.
- **LLM/API error:** Treat as “cannot answer” + offer escalation (optional: retry once before offering).
- **User says “escalate” without prior offer:** Either ignore, or treat as “I couldn’t answer; here’s the offer” then confirm in same turn (implementation choice; see below).

**Session / context**

- “User confirms” only makes sense in the **same logical conversation** after an “offer escalation” response. So the **caller** (terminal, uagents, future API) must either:
  - Keep **session/conversation context** and pass “this is a follow-up to the last message,” or
  - Pass **last engine output** (e.g. “last response was offer_escalation”) so the engine can interpret “yes” as confirmation.

We’ll make this explicit in the implementation (who holds “we just offered escalation”).

---

## 2. Implementation approach

### 2.1 Engine output: not just a string

Today the engine returns a single string. To support “offer escalation” and “user confirmed,” we need the engine to:

- Return a **structured outcome** so the caller knows what happened and what to do next.
- Accept **context** so it can recognize “user is confirming escalation” on the next turn.

Proposed **engine output** (conceptually):

- `answer` – We have a normal answer; show it. No escalation.
- `cannot_answer` – We couldn’t answer; message to show + **offer_escalation = true** (so caller can show the message and treat the next user message as potential confirmation).
- `escalated` – We just performed escalation; message to show (“I’ve escalated; someone will follow up”).

So the engine stays the single place that decides “can answer / cannot answer” and “user confirmed → escalate.” The **caller** only needs to:

- Send the user’s raw message (and optionally “last outcome” or “pending escalation offer”).
- Show the string the engine returns.
- If the engine said “offer_escalation,” the **next** message from the user can be interpreted by the engine as confirm / not confirm.

### 2.2 Where “pending escalation” state lives

Two options:

- **A) Caller holds state**  
  Caller stores “last outcome was offer_escalation” and the original question. On next message, if user said “yes”/“escalate,” caller calls something like `engine.confirm_escalate(original_question)` and then shows the result.  
  Pro: Engine stays stateless. Con: Caller must track state and pass it back.

- **B) Engine holds session state**  
  Engine has a `session_id` or `conversation_id` and stores “last response was offer_escalation + question” per session. Next message with same session is interpreted as follow-up.  
  Pro: Caller stays dumb (message in, message out per session). Con: Engine (or a small “conversation manager”) must be stateful.

**Recommendation:** Start with **A** (caller holds state). It’s explicit, easy to test, and works the same for terminal, uagents, and future HTTP API. We can introduce a small “session context” object that the caller maintains and passes in.

So:

- **Input to engine:** `(message: str, context: Optional[SessionContext])`
- **SessionContext:** e.g. `last_outcome: Literal["answer", "cannot_answer", "escalated"] | None`, and optionally `pending_question: str | None` when `last_outcome == "cannot_answer"`.
- **Output:** A small **result object**: `text: str`, `outcome: "answer" | "cannot_answer" | "escalated"`, and maybe `pending_question: str | None` when we’re offering escalation (so caller can store it for the next turn).

When the engine sees `context.last_outcome == "cannot_answer"` and the user message looks like a confirmation, it calls the escalation sender, returns outcome `"escalated"`, and the caller updates context to `last_outcome = "escalated"` and clears pending question.

### 2.3 Flow inside the engine (pseudocode)

```
def process(message, context, escalation_sender=None):
  if context and context.last_outcome == "cannot_answer" and is_escalation_confirmation(message):
    if escalation_sender:
      escalation_sender.send(...)  # include context.pending_question and maybe message
    return Result(text="I've escalated this; the committee will follow up.", outcome="escalated")
  # Normal path: try to answer
  answer, can_answer = try_answer(message)  # LLM + “can I answer?” (e.g. structured output or second call)
  if can_answer:
    return Result(text=answer, outcome="answer")
  # Cannot answer
  return Result(
    text=answer + " Would you like me to escalate this to the committee?",
    outcome="cannot_answer",
    pending_question=message,
  )
```

So we need:

- A way for the engine to know “can answer” vs “cannot answer” (e.g. LLM instructed to say so, or structured output).
- A clear **confirmation detector**: `is_escalation_confirmation(message)` (e.g. “yes”, “escalate”, “please escalate”, “sure” in reply to offer).

---

## 3. Interfaces to plug in

### 3.1 Escalation sender (injectable)

We already have a Discord client. Abstract it behind a small interface so the engine doesn’t depend on Discord:

- **Interface (e.g. in `escalation/interface.py` or `escalation/base.py`):**

  ```python
  class EscalationSender(Protocol):
      def send(self, user_question: str, user_message: str | None = None) -> None:
          """Send an escalation request (e.g. ping committee). Optional extra context."""
          ...
  ```

- **Discord implementation:** `DiscordWebhookClient` implements this: format `user_question` (and optional `user_message`) into the webhook body, ping role, execute.
- **QAEngine** takes `Optional[EscalationSender]` in `__init__`. When it decides to escalate (user confirmed), it calls `escalation_sender.send(pending_question, current_message)`.

So: **one interface, one concrete implementation (Discord);** easy to add Slack/email later.

### 3.2 Engine input/output

- **Input:**
  - `message: str`
  - `context: Optional[SessionContext]`  
    - `SessionContext`: `last_outcome: Literal["answer","cannot_answer","escalated"] | None`, `pending_question: str | None`
- **Output:** A **Result** (or named tuple) with:
  - `text: str` – always present; what to show the user.
  - `outcome: Literal["answer", "cannot_answer", "escalated"]`
  - `pending_question: str | None` – set when `outcome == "cannot_answer"` so caller can store it for confirmation.

Callers (terminal, uagents, API) will:

- Maintain `SessionContext` (or equivalent) per user/session.
- After each call, update context from the result (`last_outcome`, `pending_question`).
- Pass context back on the next call.

### 3.3 Caller contract (terminal / uagents / API)

- **Terminal (run_local.py):**  
  - One “session” per run. Keep `SessionContext` in a variable.  
  - Loop: read input → `result = engine.process(message, context, escalation_sender)` → print `result.text` → update context from `result`.

- **uagents (agent.py):**  
  - Session = per-sender (e.g. sender address). Store context in agent state or a small store keyed by sender.  
  - On each message: load context → `engine.process(...)` → send `result.text` → save context.

- **Future HTTP API:**  
  - Session = session id or user id. Same pattern: load context, call engine, return `result.text`, persist context.

No need to change the **external** contract (e.g. “one message in, one message out” per request); we only add an optional context in/out so that “user confirms escalation” is possible.

---

## 4. Summary

| What | Decision |
|------|----------|
| **When we escalate** | Only when we **cannot** answer **and** the user **confirms** (after we offer). |
| **Who holds “pending escalation” state** | Caller (recommended): pass `SessionContext` in, get `outcome` + `pending_question` out. |
| **Engine output** | Structured result: `text`, `outcome` (`answer` \| `cannot_answer` \| `escalated`), `pending_question` when offering. |
| **Escalation backend** | Abstract `EscalationSender`; Discord implementation; inject into engine. |
| **Confirmation** | Engine interprets next user message when `context.last_outcome == "cannot_answer"`; explicit “yes”/“escalate” etc. |

Next steps for implementation:

1. Add `SessionContext` and engine **Result** type (and `process(..., context, escalation_sender)`).
2. Implement “can answer” vs “cannot answer” in the engine (LLM or structured output).
3. Implement `is_escalation_confirmation(message)` and the confirmation → `escalation_sender.send(...)` path.
4. Add `EscalationSender` protocol and make `DiscordWebhookClient` implement it.
5. Wire engine to optional `EscalationSender` and update callers (run_local, agent) to pass context and use result.

If you want, we can next turn this into concrete type stubs and function signatures in the repo (e.g. `escalation/interface.py`, `qa_engine/types.py`, and changes to `qa_engine/engine.py`).
