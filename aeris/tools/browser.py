from __future__ import annotations

import urllib.parse
import webbrowser
from urllib.parse import urlparse

from ..models import ActionResult


class BrowserTools:
    def __init__(self, allowed_domains: tuple[str, ...]):
        self.allowed_domains = tuple(domain.lower() for domain in allowed_domains)

    def _normalize_url(self, value: str) -> str:
        candidate = value.strip()
        if "://" in candidate and not candidate.startswith(("http://", "https://")):
            raise ValueError("Only valid HTTP and HTTPS URLs are allowed.")
        if not candidate.startswith(("http://", "https://")):
            candidate = "https://" + candidate
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only valid HTTP and HTTPS URLs are allowed.")
        hostname = parsed.hostname.lower()
        if "*" not in self.allowed_domains and not any(
            hostname == domain or hostname.endswith("." + domain) for domain in self.allowed_domains
        ):
            raise ValueError(f"Domain is not allowed: {hostname}")
        return candidate

    def open_url(self, arguments: dict[str, object]) -> ActionResult:
        url = self._normalize_url(str(arguments["url"]))
        opened = webbrowser.open(url, new=2)
        if not opened:
            return ActionResult(
                False, "The default browser did not accept the request.", error="browser_open_failed"
            )
        return ActionResult(True, f"Opened {url}", data={"url": url})

    def search_web(self, arguments: dict[str, object]) -> ActionResult:
        query = str(arguments["query"]).strip()
        if not query:
            return ActionResult(False, "Search query cannot be empty.", error="empty_query")
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        return self.open_url({"url": url})

    def search_youtube(self, arguments: dict[str, object]) -> ActionResult:
        query = str(arguments["query"]).strip()
        if not query:
            return ActionResult(False, "YouTube query cannot be empty.", error="empty_query")
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
        return self.open_url({"url": url})
