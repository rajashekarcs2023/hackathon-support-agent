# Escalation flow

We only escalate when **both** (1) we cannot answer the question, and (2) the user confirms.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. User sends a message                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Engine tries to answer (hackathon Q&A)                                    │
│    Decides: "can answer" vs "cannot answer"                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │ CAN answer            │       │ CANNOT answer          │
        │ → Return answer        │       │ → Return explanation   │
        │   (done)               │       │   + offer escalation   │
        └───────────────────────┘       └───────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. User sees: "I couldn't answer … Would you like me to escalate to the     │
│    committee?"                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. User sends follow-up                                                      │
│    "Yes" / "escalate" / "please" → confirmation                             │
│    Anything else → new question, go to step 1                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │ User CONFIRMS         │       │ User does NOT confirm │
        │ → Perform escalation  │       │ → No ping, respond     │
        │   (e.g. Discord ping)  │       │   as normal            │
        │ → Tell user "Done"    │       └───────────────────────┘
        └───────────────────────┘
```
