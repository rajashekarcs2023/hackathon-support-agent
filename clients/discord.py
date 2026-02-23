"""Discord webhook wrapper."""

from discord_webhook import DiscordWebhook


class DiscordWebhookClient:
    def __init__(self, webhook_url: str, role_id: str):
        self.webhook_url = webhook_url
        self.role_id = role_id

    def send(self, message: str):
        if self.role_id:
            content = f"<@&{self.role_id}> {message}"
            allowed_mentions = {"roles": [self.role_id]}
        else:
            content = message
            allowed_mentions = {"parse": []}

        webhook = DiscordWebhook(
            url=self.webhook_url,
            content=content,
            allowed_mentions=allowed_mentions,
        )
        return webhook.execute()
