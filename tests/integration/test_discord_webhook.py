import os

import pytest

from clients.discord import DiscordWebhookClient


@pytest.mark.integration
def test_discord_webhook_send():
    """Integration test: sends a real message to Discord webhook.
    Requires DISCORD_WEBHOOK_URL to be set (e.g. in .env).
    Fails if the env var is missing."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    assert webhook_url, "DISCORD_WEBHOOK_URL environment variable is required for integration test"

    client = DiscordWebhookClient(webhook_url=webhook_url, role_id="")
    response = client.send("Integration test – safe to ignore")

    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
