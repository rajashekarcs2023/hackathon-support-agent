"""Discord webhook escalation channel."""

from discord_webhook import DiscordWebhook


class DiscordWebhookClient:
    def __init__(self, webhook_url: str, role_id: str):
        self.webhook_url = webhook_url
        self.role_id = role_id

    def send(self, message: str):
        webhook = DiscordWebhook(
            url=self.webhook_url,
            content=f"<@&{self.role_id}> {message}",
            allowed_mentions={"roles": [self.role_id]},
        )
        return webhook.execute()
