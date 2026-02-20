"""Uagents chat protocol adapter: receives messages, calls QA engine, optionally escalates on failure."""

from datetime import datetime
from uuid import uuid4

from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from qa_engine.engine import QAEngine, DEFAULT_FALLBACK


def create_agent(
    agent_seed: str,
    qa_engine: QAEngine,
    escalation=None,
    *,
    name: str = "ASI-agent",
    port: int = 8001,
):
    """Build and return a uagents Agent that uses the given QA engine and optional escalation."""
    agent = Agent(
        name=name,
        seed=agent_seed,
        port=port,
        mailbox=True,
        publish_agent_details=True,
    )
    protocol = Protocol(spec=chat_protocol_spec)

    @protocol.on_message(ChatMessage)
    async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
        await ctx.send(
            sender,
            ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
        )

        text = ""
        for item in msg.content:
            if isinstance(item, TextContent):
                text += item.text

        response = DEFAULT_FALLBACK
        try:
            response = qa_engine.answer(text)
        except Exception:
            ctx.logger.exception("Error querying model")
            if escalation is not None and hasattr(escalation, "send"):
                escalation.send(f"QA failed for question: {text[:200]}")

        await ctx.send(
            sender,
            ChatMessage(
                timestamp=datetime.now(datetime.timezone.utc),
                msg_id=uuid4(),
                content=[
                    TextContent(type="text", text=response),
                    EndSessionContent(type="end-session"),
                ],
            ),
        )

    @protocol.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass

    agent.include(protocol, publish_manifest=True)
    return agent
