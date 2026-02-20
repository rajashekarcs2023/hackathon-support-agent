"""Entrypoint: validate env, wire layers, run the uagents adapter."""

from env import config, require_env
from qa_engine.engine import QAEngine
from escalation.discord import DiscordWebhookClient
from adapters.uagents_agent import create_agent


def main() -> None:
    require_env()
    qa_engine = QAEngine(openai_api_key=config.OPENAI_API_KEY)
    escalation = DiscordWebhookClient(
        webhook_url=config.DISCORD_WEBHOOK_URL,
        role_id=config.DISCORD_ROLE_ID,
    )
    agent = create_agent(
        agent_seed=config.AGENT_SEED_PHRASE,
        qa_engine=qa_engine,
        escalation=escalation,
    )
    agent.run()


if __name__ == "__main__":
    main()
