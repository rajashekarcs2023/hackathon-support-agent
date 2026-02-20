from discord_webhook import DiscordWebhook

from env import config


class DiscordWebhookClient:
    def __init__(self):
        self.webhook_url = config.DISCORD_WEBHOOK_URL
        self.role_id = config.DISCORD_ROLE_ID

    def send(self, message: str):
        webhook = DiscordWebhook(
            url=self.webhook_url,
            content=f"<@&{self.role_id}> {message}",
            allowed_mentions={"roles": [self.role_id]}
        )
        return webhook.execute()
