"""QA engine: ReAct-style agent with multi-turn conversation state.

Purpose
-------
The QA engine is the single place that owns "handle this message." Callers (e.g.
terminal chatbot, uagents agent, future HTTP API) do one thing: pass in a message
and a session_id, get back a message. Orchestration—answering from knowledge,
optional escalation on failure or special cases—lives inside the engine. Callers
are not responsible for branching or retries.

Interface contract
------------------
- **Input:** One message (string) + session_id (string).
- **Output:** One message (string). The engine always returns something the caller
  can show or send back (e.g. an answer, a fallback like "Unable to answer...", or
  "I've escalated this; someone will follow up").
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

from qa_engine.store import (
    HISTORY_LIMIT,
    ConversationContext,
    ConversationStore,
    InMemoryConversationStore,
)

logger = logging.getLogger(__name__)

# Scope: hackathon Q&A bot
SCOPE_DESCRIPTION = (
    "this hackathon: event info, schedule, rules, logistics, prizes, "
    "sponsors, workshops, judging, and other hackathon-related questions"
)

DEFAULT_FALLBACK = "Unable to answer your question at this time"

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_docs",
            "description": (
                "Search the knowledge base to find an answer to the user's question. "
                "Use this when you need factual information about the hackathon."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up in the knowledge base.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "offer_escalation",
            "description": (
                "Offer to escalate to a human organizer. Use this when: "
                "(1) you cannot answer from available knowledge, OR "
                "(2) the participant is in distress, upset, or reporting an urgent "
                "situation (e.g. theft, injury, harassment, lost item, medical issue, "
                "safety concern) — even if the topic is not a typical Q&A question, OR "
                "(3) the participant needs real-time or on-the-ground information that "
                "the static knowledge base cannot reliably provide (e.g. why food is "
                "late today, where an organizer currently is, live status of an "
                "event). First answer from the knowledge base when the question is "
                "about scheduled meal times (when is food, what time is lunch, etc.); "
                "only escalate for live/operational issues (e.g. 'food still hasn't "
                "arrived', 'I didn't get food'). Never tell the participant to 'ask a "
                "volunteer' or 'check on-site' — escalate instead so an organizer can "
                "follow up directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_escalation",
            "description": (
                "Confirm and execute the escalation after the user has agreed to escalate."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


class QAEngine:
    """Handles a user message and returns a single response message.

    Uses a ReAct-style loop with OpenAI tool calls for routing. Conversation
    state (history + escalation flag) is stored in a ConversationStore so that
    multi-turn interactions work correctly across calls.
    """

    def __init__(self, openai_api_key: str, store: ConversationStore | None = None):
        self._client = OpenAI(api_key=openai_api_key)
        self._store = store or InMemoryConversationStore()

    def answer(self, message: str, session_id: str = "default") -> str:
        """Process a user message and return a response.

        Implements the engine contract: one message in, one message out. The
        caller can always use the return value as the reply to show or send.
        Escalation is handled inside this flow.
        """
        ctx = self._store.load(session_id)
        reply = self._run_react(message, ctx)
        self._store.save(session_id, ctx)
        return reply

    def _build_system_prompt(self, ctx: ConversationContext) -> str:
        now = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
        current_time = now.strftime("%A, %B %-d, %Y at %-I:%M %p %Z")
        base = (
            f"You are a helpful hackathon Q&A assistant. "
            f"The current date and time is {current_time}. "
            f"Use this when answering time-sensitive questions — for example, if a meal "
            f"or event is already in the past, say so rather than presenting it as upcoming. "
            f"Answer questions about {SCOPE_DESCRIPTION}. "
            f"If a participant is in distress, upset, or reporting an urgent situation "
            f"(theft, injury, harassment, safety concern, or anything requiring immediate "
            f"human attention), call offer_escalation — do NOT redirect them away. "
            f"For genuinely off-topic questions unrelated to the event or participant "
            f"wellbeing, politely redirect to hackathon topics. "
            f"Use retrieve_docs to look up factual information, offer_escalation when "
            f"you cannot answer or when a participant needs human help, and "
            f"confirm_escalation when the user agrees to escalate."
        )
        if ctx.pending_escalation:
            base += (
                "\n\nIMPORTANT: pending_escalation=True. If user confirms escalation "
                "(yes/please/escalate), call confirm_escalation. Otherwise treat as a new question."
            )
        return base

    def _run_react(self, message: str, ctx: ConversationContext) -> str:
        ctx.history.append({"role": "user", "content": message})

        messages = [
            {"role": "system", "content": self._build_system_prompt(ctx)},
            *ctx.history[-HISTORY_LIMIT:],
        ]

        reply = DEFAULT_FALLBACK

        for _ in range(3):
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
                max_tokens=2048,
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                reply = msg.content or DEFAULT_FALLBACK
                break

            messages.append(msg)

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")

                if tool_name == "retrieve_docs":
                    result = self._tool_retrieve_docs(args.get("query", ""), messages)
                    ctx.pending_escalation = False
                elif tool_name == "offer_escalation":
                    result = self._tool_offer_escalation()
                    ctx.pending_escalation = True
                elif tool_name == "confirm_escalation":
                    result = self._tool_confirm_escalation()
                    ctx.pending_escalation = False
                else:
                    result = f"Unknown tool: {tool_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        ctx.history.append({"role": "assistant", "content": reply})
        ctx.history = ctx.history[-HISTORY_LIMIT:]

        return reply

    def _get_knowledge(self) -> dict:
        knowledge_path = Path(__file__).parent.parent / "hackathonknowledge.json"
        with open(knowledge_path) as f:
            return json.load(f)

    def _tool_retrieve_docs(self, query: str, messages: list[dict]) -> str:
        knowledge = self._get_knowledge()
        knowledge_text = json.dumps(knowledge, indent=2)
        now = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
        current_time = now.strftime("%A, %B %-d, %Y at %-I:%M %p %Z")
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a knowledge base assistant for a hackathon. "
                        "Answer the following query using ONLY the information provided "
                        "below. Each key includes a 'semantic_description' that explains "
                        "what it covers — use those descriptions to find the relevant section. "
                        "Current date and time (use for time-sensitive answers): "
                        f"{current_time}. "
                        "When answering about meals or schedule, say whether a time has "
                        "already passed or is upcoming based on the current time. "
                        "If the answer is not present in the knowledge base, say so clearly "
                        "and do not invent information.\n\n"
                        f"HACKATHON KNOWLEDGE BASE:\n{knowledge_text}"
                    ),
                },
                {"role": "user", "content": query},
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content or DEFAULT_FALLBACK

    def _tool_offer_escalation(self) -> str:
        return "I couldn't find a confident answer to your question. Would you like me to escalate this to a human organizer who can help you directly?"

    def _tool_confirm_escalation(self) -> str:
        logger.info("Escalation confirmed by user.")
        return "I've escalated your question to the hackathon organizers. Someone will follow up with you shortly!"
