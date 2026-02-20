import os
import pytest
from unittest.mock import patch, MagicMock
from discord_client import DiscordWebhookClient


def test_client_initializes():
    with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test", "DISCORD_ROLE_ID": "123456789"}):
        client = DiscordWebhookClient()
        assert client.webhook_url == "https://discord.com/api/webhooks/test"
        assert client.role_id == "123456789"


def test_send_message():
    with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test", "DISCORD_ROLE_ID": "123456789"}):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("discord_client.DiscordWebhook") as MockWebhook:
            mock_webhook_instance = MagicMock()
            mock_webhook_instance.execute.return_value = mock_response
            MockWebhook.return_value = mock_webhook_instance

            client = DiscordWebhookClient()
            response = client.send("Test alert message")

            MockWebhook.assert_called_once_with(
                url="https://discord.com/api/webhooks/test",
                content="<@&123456789> Test alert message",
                allowed_mentions={"roles": ["123456789"]}
            )
            mock_webhook_instance.execute.assert_called_once()
            assert response.status_code >= 200
            assert response.status_code < 300
