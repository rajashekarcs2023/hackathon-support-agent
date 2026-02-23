"""Discord escalation: notifies organizers via webhook."""

import logging

from clients.discord import DiscordWebhookClient
from escalation.base_escalation import BaseEscalation

logger = logging.getLogger(__name__)


class DiscordEscalation(BaseEscalation):
    """Escalates by posting a message to a Discord channel via webhook."""

    def __init__(self, client: DiscordWebhookClient, message_prefix: str = ""):
        self._client = client
        self._message_prefix = message_prefix

    def escalate(self, user_message: str) -> str:
        parts = [p for p in [self._message_prefix, user_message] if p]
        content = " ".join(parts) if parts else user_message

        try:
            response = self._client.send(content)
            if response.status_code in (200, 204):
                logger.info("Discord escalation succeeded (status %d)", response.status_code)
                return (
                    "Escalation sent successfully. "
                    "The organizers have been notified on Discord and will follow up shortly."
                )
            else:
                logger.warning(
                    "Discord escalation returned unexpected status %d", response.status_code
                )
                return (
                    f"Escalation attempt returned an unexpected status ({response.status_code}). "
                    "Please try again or find an organizer directly."
                )
        except Exception as e:
            logger.exception("Discord escalation failed: %s", e)
            return (
                "Failed to send escalation due to a technical error. "
                "Please try again or find an organizer directly."
            )
