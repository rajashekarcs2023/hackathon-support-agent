import pytest
from unittest.mock import patch, MagicMock
from escalation.discord import DiscordWebhookClient


@pytest.mark.unit
def test_client_initializes():
    client = DiscordWebhookClient(
        webhook_url="https://discord.com/api/webhooks/test",
        role_id="123456789",
    )
    assert client.webhook_url == "https://discord.com/api/webhooks/test"
    assert client.role_id == "123456789"


@pytest.mark.unit
def test_send_message():
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("escalation.discord.DiscordWebhook") as MockWebhook:
        mock_webhook_instance = MagicMock()
        mock_webhook_instance.execute.return_value = mock_response
        MockWebhook.return_value = mock_webhook_instance

        client = DiscordWebhookClient(
            webhook_url="https://discord.com/api/webhooks/test",
            role_id="123456789",
        )
        response = client.send("Test alert message")

        MockWebhook.assert_called_once_with(
            url="https://discord.com/api/webhooks/test",
            content="<@&123456789> Test alert message",
            allowed_mentions={"roles": ["123456789"]},
        )
        mock_webhook_instance.execute.assert_called_once()
        assert response.status_code >= 200
        assert response.status_code < 300
