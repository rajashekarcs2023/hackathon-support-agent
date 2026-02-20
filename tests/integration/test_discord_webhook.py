import os
import pytest
from discord_client import DiscordWebhookClient


@pytest.mark.integration
def test_discord_webhook_send():
    """Integration test: sends a real message to Discord webhook.
    Requires DISCORD_WEBHOOK_URL and DISCORD_ROLE_ID to be set.
    Fails if env vars are missing."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    role_id = os.getenv("DISCORD_ROLE_ID")
    
    assert webhook_url, "DISCORD_WEBHOOK_URL environment variable is required for integration test"
    assert role_id, "DISCORD_ROLE_ID environment variable is required for integration test"
    
    client = DiscordWebhookClient()
    response = client.send("Integration test – safe to ignore")
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
