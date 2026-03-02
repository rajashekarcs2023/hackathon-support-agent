"""Discord bot client: reads messages from a channel via the REST API."""

import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://discord.com/api/v10"


class DiscordBotClient:
    """Read-only Discord client that fetches messages from a channel.

    Paginates through the full channel history and caches results in memory
    so that knowledge accumulates over the lifetime of the process.
    """

    def __init__(self, bot_token: str, channel_id: str):
        self._bot_token = bot_token
        self._channel_id = channel_id
        self._headers = {"Authorization": f"Bot {bot_token}"}
        self._cache: list[dict] = []
        self._latest_id: str | None = None  # track newest message seen

    def fetch_messages(self) -> list[dict]:
        """Fetch all human messages from the configured channel.

        On the first call, paginates backwards through the full channel
        history.  On subsequent calls, only fetches new messages since the
        last known message, and appends them to the cache.  Returns the
        full accumulated list oldest-first.
        """
        try:
            new_msgs = (
                self._fetch_new_messages()
                if self._latest_id
                else self._fetch_all_messages()
            )
            if new_msgs:
                self._cache.extend(new_msgs)
                self._latest_id = new_msgs[-1]["id"]
            elif not self._latest_id and self._cache:
                self._latest_id = self._cache[-1]["id"]
            return self._cache

        except Exception:
            logger.exception("Failed to fetch messages from Discord channel %s", self._channel_id)
            return self._cache  # return stale cache on error

    def _fetch_page(self, params: dict) -> list[dict]:
        """Fetch a single page of messages from the Discord API."""
        url = f"{_BASE_URL}/channels/{self._channel_id}/messages"
        resp = requests.get(url, headers=self._headers, params=params, timeout=10)
        if resp.status_code != 200:
            logger.warning(
                "Discord API returned status %d: %s", resp.status_code, resp.text[:200]
            )
            return []
        return resp.json()

    def _parse_messages(self, raw_messages: list[dict]) -> list[dict]:
        """Filter and normalise raw Discord messages."""
        results = []
        for msg in raw_messages:
            if msg.get("author", {}).get("bot", False):
                continue
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            results.append({
                "id": msg["id"],
                "author": msg["author"].get("username", "unknown"),
                "content": content,
                "timestamp": msg.get("timestamp", ""),
            })
        return results

    def _fetch_all_messages(self) -> list[dict]:
        """Paginate backwards through the full channel history."""
        all_msgs: list[dict] = []
        before: str | None = None

        while True:
            params: dict = {"limit": 100}
            if before:
                params["before"] = before
            page = self._fetch_page(params)
            if not page:
                break
            all_msgs.extend(page)
            if len(page) < 100:
                break
            before = page[-1]["id"]

        # Discord returns newest-first; reverse to oldest-first, then parse
        all_msgs.reverse()
        return self._parse_messages(all_msgs)

    def _fetch_new_messages(self) -> list[dict]:
        """Fetch only messages newer than the last seen message."""
        new_msgs: list[dict] = []
        after = self._latest_id

        while True:
            params: dict = {"limit": 100, "after": after}
            page = self._fetch_page(params)
            if not page:
                break
            new_msgs.extend(page)
            if len(page) < 100:
                break
            after = page[-1]["id"]  # oldest in page; advance cursor forward

        new_msgs.reverse()  # oldest-first
        return self._parse_messages(new_msgs)

    def format_as_knowledge(self, max_messages: int = 500) -> str:
        """Fetch messages and format them as a knowledge text block.

        Only includes the most recent *max_messages* to avoid exceeding the
        LLM context window.  Returns an empty string if no messages are
        available.
        """
        messages = self.fetch_messages()
        if not messages:
            return ""

        recent = messages[-max_messages:]
        lines = []
        for msg in recent:
            lines.append(f"[{msg['author']}]: {msg['content']}")
        return "\n".join(lines)
