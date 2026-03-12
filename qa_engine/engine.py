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

import functools
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

from clients.discord_bot import DiscordBotClient
from clients.google_doc import GoogleDocClient
from clients.notion import NotionClient
from escalation.base_escalation import BaseEscalation
from qa_engine.store import (
    HISTORY_LIMIT,
    ConversationContext,
    ConversationStore,
    InMemoryConversationStore,
)

logger = logging.getLogger(__name__)

# Debug: truncate long strings in logs
def _truncate(s: str, max_len: int = 400) -> str:
    if not isinstance(s, str):
        s = str(s)
    return s[:max_len] + "..." if len(s) > max_len else s


def log_tool_call(fn):
    """Decorator: log tool name, sanitized args, result, and duration for every tool call."""
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        name = fn.__name__
        # Don't log large lists (e.g. conversation messages)
        def safe(v):
            if isinstance(v, list) and len(v) > 2:
                return f"<list of {len(v)} items>"
            return _truncate(repr(v), 200)
        safe_args = [safe(a) for a in args]
        safe_kw = {k: safe(v) for k, v in kwargs.items()}
        logger.info("Tool call: %s args=%s kwargs=%s", name, safe_args, safe_kw)
        start = time.perf_counter()
        try:
            result = fn(self, *args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info("Tool %s returned in %.3fs: %s", name, elapsed, _truncate(result))
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.exception("Tool %s failed after %.3fs: %s", name, elapsed, e)
            raise
    return wrapper

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
                "Use this for any factual question about the hackathon or sponsors "
                "(e.g. prizes, internships, careers, contact info, schedule). "
                "Call this first before concluding the KB has no answer."
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
                "Offer to escalate to a human organizer. "
                "PREREQUISITE: You MUST call retrieve_docs FIRST before calling this "
                "tool — even for distress or urgent situations. retrieve_docs checks "
                "both the knowledge base AND the live FAQ channel where organizers may "
                "have already posted guidance. Only call offer_escalation AFTER "
                "retrieve_docs confirms the information is not available. "
                "Call this ONLY when retrieve_docs could NOT answer the question — "
                "the info was not in the KB or FAQ channel. Examples: "
                "(1) retrieve_docs explicitly said the info is not available, OR "
                "(2) the participant needs real-time info that retrieve_docs could not "
                "provide. "
                "Do NOT call this tool if retrieve_docs already returned useful "
                "guidance — instead, answer the user directly using retrieve_docs "
                "result and mention you can also escalate if they need more help. "
                "Do NOT suggest 'check their website' or 'contact the sponsor'; "
                "escalate so an organizer can help. "
                "Never tell the participant to 'ask a volunteer' or 'check on-site' — "
                "escalate instead so an organizer can follow up directly. "
                "IMPORTANT: The return value of this tool IS the message to show the "
                "user. After calling this tool, relay its return value verbatim as your "
                "final reply. Do NOT call this tool again or call any other tool."
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
                "Confirm and execute the escalation after the user has agreed to escalate. "
                "This notifies the organizers (e.g. via Discord) so they can follow up. "
                "The tool result will be a plain-English string indicating success or failure. "
                "Use it to craft a warm, reassuring reply: if it succeeded, confirm the "
                "escalation was sent and that someone will follow up; if it failed, "
                "apologise and suggest the user find an organizer directly."
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

    def __init__(
        self,
        openai_api_key: str,
        knowledge_base_path: str | Path | None = None,
        store: ConversationStore | None = None,
        escalation: BaseEscalation | None = None,
        faq_client: DiscordBotClient | None = None,
        google_doc_client: GoogleDocClient | None = None,
        notion_client: NotionClient | None = None,
    ):
        self._client = OpenAI(api_key=openai_api_key)
        self._knowledge_base_path = (
            Path(knowledge_base_path)
            if knowledge_base_path
            else Path(__file__).parent.parent / "hackathonknowledge.json"
        )
        self._store = store or InMemoryConversationStore()
        self._escalation = escalation
        self._faq_client = faq_client
        self._google_doc_client = google_doc_client
        self._notion_client = notion_client

    def answer(self, message: str, session_id: str = "default") -> str:
        """Process a user message and return a response.

        Implements the engine contract: one message in, one message out. The
        caller can always use the return value as the reply to show or send.
        Escalation is handled inside this flow.
        """
        # Guard: skip the entire pipeline for empty / whitespace-only messages
        if not message or not message.strip():
            logger.info("Skipping empty message for session %s", session_id)
            return (
                "Hi! I'm the hackathon Q&A bot. "
                "Ask me anything about the event — schedule, rules, prizes, logistics, and more!"
            )
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
            f"IMPORTANT: When you find a clear answer in the knowledge retrieval result, "
            f"just answer the question directly. Do NOT offer escalation on every reply. "
            f"Only mention escalation in these specific cases: "
            f"(1) The knowledge retrieval result does NOT contain the answer — call offer_escalation. "
            f"(2) The participant is in distress or reporting an urgent situation "
            f"(theft, injury, harassment, safety concern, lost item) — share the info you found "
            f"AND end with 'Would you like me to escalate this to an organizer as well?' "
            f"(3) The user explicitly asks to escalate. "
            f"For normal questions like 'what's the schedule?' or 'how do I apply?' where you "
            f"have a confident answer, just answer. No escalation offer needed. "
            f"CRITICAL: ALWAYS call retrieve_docs as your FIRST action for ANY question — "
            f"even if you are unsure whether it is hackathon-related. The knowledge base "
            f"includes a live Google Doc and FAQ channel that may contain information you "
            f"cannot predict. Only skip retrieve_docs for clearly casual messages like "
            f"'hi' or 'thanks'. Do not answer from general knowledge — if retrieve_docs "
            f"does not contain the answer, that counts as 'cannot answer': call "
            f"offer_escalation. Do not suggest the user go elsewhere (e.g. 'check the "
            f"careers page', 'contact the sponsor') instead of escalating; offer "
            f"escalation so an organizer can help. "
            f"If the user explicitly asks to escalate or talk to an organizer "
            f"(e.g. 'I want to escalate', 'connect me to an organizer', 'escalate this'), "
            f"call confirm_escalation immediately — treat it as confirmed consent to escalate."
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
        logger.info("ReAct loop starting for user message: %s", _truncate(message, 120))

        # Always run retrieve_docs upfront so the model has KB + FAQ + Google
        # Doc context before deciding how to respond.
        # Skip for very short non-question messages (greetings, thanks, etc.)
        stripped = message.strip().lower().rstrip("!?.")
        casual = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "goodbye", "yo", "sup"}
        if stripped in casual:
            logger.info("Casual message detected, skipping retrieve_docs")
            kb_result = None
        else:
            kb_result = self._tool_retrieve_docs(message, messages)
        messages.append({
            "role": "system",
            "content": (
                f"Knowledge retrieval result for the user's message:\n{kb_result}"
            ),
        })

        for step in range(3):
            logger.info("ReAct step %d: calling model (messages=%d)", step + 1, len(messages))
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
                logger.info("ReAct step %d: model returned final reply (no tool calls)", step + 1)
                break

            tool_names = [tc.function.name for tc in msg.tool_calls]
            logger.info("ReAct step %d: model requested tools: %s", step + 1, tool_names)
            messages.append(msg)

            terminal_reply = None
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")

                if tool_name == "retrieve_docs":
                    result = self._tool_retrieve_docs(args.get("query", ""), messages)
                    ctx.pending_escalation = False
                elif tool_name == "offer_escalation":
                    result = self._tool_offer_escalation(ctx)
                    ctx.pending_escalation = True
                    terminal_reply = result
                elif tool_name == "confirm_escalation":
                    user_msgs = [m["content"] for m in ctx.history if m["role"] == "user"]
                    original = user_msgs[-2] if len(user_msgs) >= 2 else message
                    result = self._tool_confirm_escalation(original, ctx)
                    ctx.pending_escalation = False
                else:
                    result = f"Unknown tool: {tool_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            if terminal_reply is not None:
                reply = terminal_reply
                break

        if not msg.tool_calls or terminal_reply is not None:
            logger.info("ReAct loop finished with reply: %s", _truncate(reply, 150))
        else:
            logger.warning("ReAct loop hit max steps (3); using last reply as fallback")

        ctx.history.append({"role": "assistant", "content": reply})
        ctx.history = ctx.history[-HISTORY_LIMIT:]

        return reply

    def _get_knowledge(self) -> dict:
        with open(self._knowledge_base_path) as f:
            return json.load(f)

    def _get_faq_section(self) -> str:
        """Fetch FAQ channel messages and format as a knowledge section."""
        if not self._faq_client:
            return ""
        faq_text = self._faq_client.format_as_knowledge()
        if not faq_text:
            return ""
        return f"\n\nFAQ CHANNEL MESSAGES (organizer answers from Discord):\n{faq_text}"

    def _get_google_doc_section(self) -> str:
        """Fetch Google Doc content and format as a knowledge section."""
        if not self._google_doc_client:
            return ""
        doc_text = self._google_doc_client.get_content()
        if not doc_text:
            return ""
        return f"\n\nHACKER GUIDE (live Google Doc from organizers):\n{doc_text}"

    def _get_notion_section(self) -> str:
        """Fetch Notion page content and format as a knowledge section."""
        if not self._notion_client:
            return ""
        doc_text = self._notion_client.get_content()
        if not doc_text:
            return ""
        return f"\n\nHACKER GUIDE (live Notion page from organizers):\n{doc_text}"

    def _get_live_doc_section(self) -> str:
        """Return the live document section from whichever source is configured.

        Only one live doc source (Google Doc or Notion) should be active per
        tenant.  If both clients happen to be set, Google Doc takes precedence.
        """
        section = self._get_google_doc_section()
        if section:
            return section
        return self._get_notion_section()

    @log_tool_call
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
                        "IMPORTANT: You have three knowledge sources listed below in order "
                        "of recency: (1) HACKATHON KNOWLEDGE BASE — the baseline, "
                        "(2) HACKER GUIDE — a live document maintained by organizers that "
                        "may contain updates or additional info, and (3) FAQ CHANNEL MESSAGES "
                        "— the most recent organizer answers from Discord. "
                        "If there is a conflict between sources, the MORE RECENT source wins: "
                        "FAQ channel > Hacker Guide > Knowledge Base. "
                        "If the answer is in none of the sources, say so clearly and do not "
                        "invent information.\n\n"
                        f"HACKATHON KNOWLEDGE BASE:\n{knowledge_text}"
                        f"{self._get_live_doc_section()}"
                        f"{self._get_faq_section()}"
                    ),
                },
                {"role": "user", "content": query},
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content or DEFAULT_FALLBACK

    @log_tool_call
    def _tool_offer_escalation(self, ctx: ConversationContext) -> str:
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a warm, helpful hackathon assistant. Based on this conversation, "
                        "you were unable to find a confident answer in the knowledge base. "
                        "Write 1-2 natural, friendly sentences: acknowledge what the user was asking about, "
                        "let them know you don't have a confident answer, and offer to escalate to a "
                        "human organizer who can help them directly. Be specific to their question — "
                        "no generic filler. Do not answer the question itself."
                    ),
                },
                *ctx.history[-HISTORY_LIMIT:],
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content or (
            "I don't have a confident answer for that — would you like me to loop in a human organizer?"
        )

    @log_tool_call
    def _tool_confirm_escalation(self, user_message: str, ctx: ConversationContext) -> str:
        if self._escalation:
            return self._escalation.escalate(user_message)
        logger.info("Escalation confirmed (no handler configured).")
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a warm, helpful hackathon assistant. The user just agreed to escalate "
                        "their question and it has been flagged for a human organizer to follow up. "
                        "Write 1-2 natural, friendly sentences confirming this and reassuring them "
                        "someone will get back to them. Be specific to what they asked — no generic filler."
                    ),
                },
                *ctx.history[-HISTORY_LIMIT:],
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content or (
            "I've passed your question along to the organizers — someone will follow up with you shortly!"
        )
