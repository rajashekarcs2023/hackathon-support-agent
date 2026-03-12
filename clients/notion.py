"""Notion client: fetches page content via the Notion API with TTL caching.

Recursively reads all blocks from a Notion page, flattens them into plain
text suitable for LLM context, and caches the result with a configurable TTL.
"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_DEFAULT_MAX_CHARS = 20000


class NotionClient:
    """Fetches a Notion page as plain text with in-memory TTL caching.

    The page must be shared with the integration whose token is provided.
    Content is truncated to *max_chars* to keep the LLM context window
    manageable.
    """

    def __init__(
        self,
        api_token: str,
        page_id: str,
        cache_ttl: int = 60,
        max_chars: int = _DEFAULT_MAX_CHARS,
    ):
        self._api_token = api_token
        self._page_id = page_id
        self._cache_ttl = cache_ttl
        self._max_chars = max_chars
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self._cached_text: str = ""
        self._last_fetch: float = 0.0

    def get_content(self) -> str:
        """Return the page text, re-fetching if the cache is stale.

        Returns an empty string if the fetch fails and no cached copy
        exists yet.
        """
        now = time.monotonic()
        if self._cached_text and (now - self._last_fetch) < self._cache_ttl:
            return self._cached_text

        try:
            blocks = self._fetch_all_blocks(self._page_id)
            text = self._flatten_blocks(blocks)
            if len(text) > self._max_chars:
                text = text[: self._max_chars] + "\n\n[... content truncated ...]"
                logger.warning(
                    "Notion page content truncated from %d to %d chars",
                    len(text),
                    self._max_chars,
                )
            self._cached_text = text.strip()
            self._last_fetch = now
            logger.info(
                "Notion page fetched successfully (%d chars)", len(self._cached_text)
            )
        except Exception:
            logger.exception("Failed to fetch Notion page %s", self._page_id)

        return self._cached_text

    # ------------------------------------------------------------------
    # Notion API helpers
    # ------------------------------------------------------------------

    def _fetch_all_blocks(self, block_id: str) -> list[dict]:
        """Fetch all child blocks of a block, handling pagination."""
        blocks: list[dict] = []
        url = f"{_API_BASE}/blocks/{block_id}/children"
        params: dict[str, Any] = {"page_size": 100}

        while True:
            resp = requests.get(
                url, headers=self._headers, params=params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            blocks.extend(results)

            # Recursively fetch children for blocks that have them
            for block in results:
                if block.get("has_children"):
                    children = self._fetch_all_blocks(block["id"])
                    block["_children"] = children

            if not data.get("has_more"):
                break
            params["start_cursor"] = data["next_cursor"]

        return blocks

    # ------------------------------------------------------------------
    # Block-to-text flattening
    # ------------------------------------------------------------------

    def _flatten_blocks(self, blocks: list[dict], depth: int = 0) -> str:
        """Convert a list of Notion blocks into readable plain text."""
        lines: list[str] = []
        indent = "  " * depth
        numbered_index = 0

        for block in blocks:
            block_type = block.get("type", "")
            text = self._extract_rich_text(block, block_type)

            if block_type in ("paragraph",):
                if text:
                    lines.append(f"{indent}{text}")
                else:
                    lines.append("")  # blank line

            elif block_type == "heading_1":
                lines.append(f"\n{indent}# {text}")

            elif block_type == "heading_2":
                lines.append(f"\n{indent}## {text}")

            elif block_type == "heading_3":
                lines.append(f"\n{indent}### {text}")

            elif block_type == "bulleted_list_item":
                lines.append(f"{indent}- {text}")
                numbered_index = 0

            elif block_type == "numbered_list_item":
                numbered_index += 1
                lines.append(f"{indent}{numbered_index}. {text}")

            elif block_type == "to_do":
                checked = block.get(block_type, {}).get("checked", False)
                marker = "[x]" if checked else "[ ]"
                lines.append(f"{indent}{marker} {text}")

            elif block_type == "toggle":
                lines.append(f"{indent}▸ {text}")

            elif block_type == "quote":
                lines.append(f"{indent}> {text}")

            elif block_type == "callout":
                emoji = block.get(block_type, {}).get("icon", {}).get("emoji", "")
                lines.append(f"{indent}{emoji} {text}")

            elif block_type == "code":
                language = block.get(block_type, {}).get("language", "")
                lines.append(f"{indent}```{language}")
                lines.append(f"{indent}{text}")
                lines.append(f"{indent}```")

            elif block_type == "divider":
                lines.append(f"{indent}---")

            elif block_type == "table_row":
                cells = block.get(block_type, {}).get("cells", [])
                row_text = " | ".join(
                    self._rich_text_to_str(cell) for cell in cells
                )
                lines.append(f"{indent}| {row_text} |")

            elif block_type in ("child_page", "child_database"):
                title = block.get(block_type, {}).get("title", "")
                lines.append(f"{indent}[{block_type}: {title}]")

            elif block_type in ("image", "video", "file", "pdf", "bookmark"):
                # Skip media blocks — not useful as text context
                pass

            else:
                # Unknown block type — include text if any
                if text:
                    lines.append(f"{indent}{text}")

            # Reset numbered index for non-numbered blocks
            if block_type != "numbered_list_item":
                numbered_index = 0

            # Recurse into children
            children = block.get("_children", [])
            if children:
                lines.append(self._flatten_blocks(children, depth + 1))

        return "\n".join(lines)

    def _extract_rich_text(self, block: dict, block_type: str) -> str:
        """Extract plain text from a block's rich_text array."""
        type_data = block.get(block_type, {})
        rich_text = type_data.get("rich_text", [])
        return self._rich_text_to_str(rich_text)

    @staticmethod
    def _rich_text_to_str(rich_text: list[dict]) -> str:
        """Join an array of Notion rich-text objects into a single string."""
        return "".join(item.get("plain_text", "") for item in rich_text)
