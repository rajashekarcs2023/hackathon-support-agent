import os
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from tenant import load_tenant
from qa_engine.engine import QAEngine

_tenant = load_tenant(os.environ.get("TENANT_CONFIG", ""))

engine = QAEngine(
    openai_api_key=_tenant.openai_api_key,
    knowledge_base_path=_tenant.knowledge_base_path,
)

agent = Agent(
    name=_tenant.agent_name,
    seed=_tenant.agent_seed,
    port=8001,
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

    response = "Unable to answer your question at this time"
    try:
        response = engine.answer(text, session_id=sender)
    except Exception:
        ctx.logger.exception("Error querying QA engine")

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(tz=timezone.utc),
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

if __name__ == "__main__":
    agent.run()
