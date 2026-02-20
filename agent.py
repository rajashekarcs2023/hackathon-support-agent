from datetime import datetime
from uuid import uuid4

from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from env import config, require_env

# Subject matter expertise
subject_matter = "the sun"

client = OpenAI(api_key=config.OPENAI_API_KEY)

agent = Agent(
    name="ASI-agent",
    seed=config.AGENT_SEED_PHRASE,
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

    text = ''
    for item in msg.content:
        if isinstance(item, TextContent):
            text += item.text

    response = 'Unable to answer your question at this time'
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""
         You are a helpful assistant who only answers questions about {subject_matter}.
         If the user asks about any other topics, politely decline.
                """},
                {"role": "user", "content": text},
            ],
            max_tokens=2048,
        )
        response = str(r.choices[0].message.content)
    except:
        ctx.logger.exception('Error querying model')

    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(datetime.timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=response),
            EndSessionContent(type="end-session"),
        ]
    ))

@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass

agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    require_env()
    agent.run()
