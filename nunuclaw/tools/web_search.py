"""Web search tool — search the web and fetch pages.

Uses httpx + BeautifulSoup for HTML-based search (DuckDuckGo).
"""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from nunuclaw.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


class WebSearchTool(BaseTool):
    """Search the web and fetch page content."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=15.0,
        )

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information and fetch page content."

    @property
    def actions(self) -> list[str]:
        return ["search", "fetch_page"]

    async def execute(self, action: str, params: dict) -> ToolResult:
        """Execute a web search action."""
        if action == "search":
            return await self._search(params)
        elif action == "fetch_page":
            return await self._fetch_page(params)
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    async def _search(self, params: dict) -> ToolResult:
        """Search the web using DuckDuckGo HTML."""
        query = params.get("query", "")
        num_results = params.get("num_results", 5)

        if not query:
            return ToolResult(success=False, error="Missing 'query' parameter")

        try:
            resp = await self._client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for result in soup.select(".result")[:num_results]:
                title_el = result.select_one(".result__title a")
                snippet_el = result.select_one(".result__snippet")

                if title_el:
                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    results.append(f"**{title}**\n{url}\n{snippet}\n")

            if results:
                output = f"🔍 Search results for: {query}\n\n" + "\n".join(results)
                return ToolResult(success=True, data=output)
            else:
                return ToolResult(
                    success=True,
                    data=f"No results found for: {query}",
                )

        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {e}")

    async def _fetch_page(self, params: dict) -> ToolResult:
        """Fetch and extract text content from a URL."""
        url = params.get("url", "")
        if not url:
            return ToolResult(success=False, error="Missing 'url' parameter")

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)

            # Truncate to reasonable length
            if len(text) > 5000:
                text = text[:5000] + "\n\n... (truncated)"

            return ToolResult(success=True, data=text)

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to fetch {url}: {e}")
