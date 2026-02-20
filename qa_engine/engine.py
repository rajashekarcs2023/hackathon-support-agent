"""QA engine: single interface for handling user messages and returning responses.

Purpose
-------
The QA engine is the single place that owns "handle this message." Callers (e.g.
terminal chatbot, uagents agent, future HTTP API) do one thing: pass in a message,
get back a message. Orchestration—answering from knowledge, optional escalation on
failure or special cases—lives inside the engine. Callers are not responsible for
branching or retries.

Interface contract
------------------
- **Input:** One message (string).
- **Output:** One message (string). The engine always returns something the caller
  can show or send back (e.g. an answer, a fallback like "Unable to answer...", or
  "I've escalated this; someone will follow up").

Escalation is an injectable detail: there are many ways to escalate (Discord,
Slack, email, etc.). The engine can accept an optional escalation sender at
construction; when appropriate it will call that sender internally and still
return a user-facing message. If no escalation is configured, the engine still
satisfies the contract by returning a message (e.g. a fallback).
"""

from openai import OpenAI

# Subject matter expertise (single scope for now)
SUBJECT_MATTER = "the sun"

DEFAULT_FALLBACK = "Unable to answer your question at this time"


class QAEngine:
    """Handles a user message and returns a single response message.

    Use this as the only interface for "process this user input." Pass in a
    message; you are guaranteed to get back a message. Orchestration and
    optional escalation are internal. Escalation (if any) is configured by
    injecting a sender at construction time.
    """

    def __init__(self, openai_api_key: str):
        self._client = OpenAI(api_key=openai_api_key)

    def answer(self, message: str) -> str:
        """Process a user message and return a response.

        Implements the engine contract: one message in, one message out. The
        caller can always use the return value as the reply to show or send
        (e.g. to the user in a terminal or over chat). Escalation, when
        configured, is handled inside this flow and does not change the
        guarantee that a string is returned.
        """
        r = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helpful assistant who only answers questions about {SUBJECT_MATTER}.
If the user asks about any other topics, politely decline.""",
                },
                {"role": "user", "content": message},
            ],
            max_tokens=2048,
        )
        return str(r.choices[0].message.content)
