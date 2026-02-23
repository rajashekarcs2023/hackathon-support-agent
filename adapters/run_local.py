"""Local terminal chatbot: type in the terminal, get QA engine responses."""

import logging
import os

from clients.discord import DiscordWebhookClient
from escalation import DiscordEscalation
from tenant import load_tenant
from qa_engine.engine import QAEngine


def _configure_logging() -> None:
    level = getattr(logging, os.getenv("LOG_LEVEL", "ERROR").upper(), logging.ERROR)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    _configure_logging()
    tenant = load_tenant(os.environ.get("TENANT_CONFIG", ""))
    discord_client = DiscordWebhookClient(tenant.discord_webhook_url, tenant.discord_role_id)
    discord_escalation = DiscordEscalation(discord_client)

    qa = QAEngine(
        openai_api_key=tenant.openai_api_key,
        knowledge_base_path=tenant.knowledge_base_path,
        escalation=discord_escalation
    )

    print(f"{tenant.agent_name}. Type 'quit' or 'exit' to stop.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        response = qa.answer(user_input, session_id="local")
        print(f"Bot: {response}\n")


if __name__ == "__main__":
    main()
