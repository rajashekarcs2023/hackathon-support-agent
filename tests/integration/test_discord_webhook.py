import pytest

from env import config
from escalation.discord import DiscordWebhookClient


@pytest.mark.integration
def test_discord_webhook_send():
    """Integration test: sends a real message to Discord webhook.
    Requires DISCORD_WEBHOOK_URL and DISCORD_ROLE_ID to be set (e.g. in .env).
    Fails if env vars are missing."""
    assert config.DISCORD_WEBHOOK_URL, "DISCORD_WEBHOOK_URL environment variable is required for integration test"
    assert config.DISCORD_ROLE_ID, "DISCORD_ROLE_ID environment variable is required for integration test"

    webhook_url = config.DISCORD_WEBHOOK_URL
    role_id = config.DISCORD_ROLE_ID

    client = DiscordWebhookClient(webhook_url=webhook_url, role_id=role_id)
    response = client.send("Integration test – safe to ignore")

    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
