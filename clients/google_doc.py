"""Google Doc client: fetches a published doc as plain text with TTL caching."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

_EXPORT_URL = "https://docs.google.com/document/d/{doc_id}/export?format=txt"


class GoogleDocClient:
    """Fetches a Google Doc as plain text with in-memory TTL caching.

    The doc must be shared as "Anyone with the link can view" for the
    export URL to work without authentication.
    """

    def __init__(self, doc_id: str, cache_ttl: int = 60):
        self._doc_id = doc_id
        self._cache_ttl = cache_ttl
        self._url = _EXPORT_URL.format(doc_id=doc_id)
        self._cached_text: str = ""
        self._last_fetch: float = 0.0

    def get_content(self) -> str:
        """Return the document text, re-fetching if the cache is stale.

        Returns an empty string if the fetch fails and no cached copy
        exists yet.
        """
        now = time.monotonic()
        if self._cached_text and (now - self._last_fetch) < self._cache_ttl:
            return self._cached_text

        try:
            resp = requests.get(self._url, timeout=10)
            if resp.status_code == 200:
                self._cached_text = resp.text.strip()
                self._last_fetch = now
                logger.info("Google Doc fetched successfully (%d chars)", len(self._cached_text))
            else:
                logger.warning(
                    "Google Doc fetch returned status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception:
            logger.exception("Failed to fetch Google Doc %s", self._doc_id)

        return self._cached_text
