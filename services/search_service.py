import os
import asyncio
import logging
import urllib.parse
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SearchService:
    """
    Service responsible for constructing dynamic scholarship search queries
    and retrieving official web search results via Tavily or DuckDuckGo HTTP.
    Uses pure httpx + beautifulsoup4 for 100% native compatibility.
    """

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    async def _search_tavily(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Executes search via official Tavily Search API if key is present."""
        results: List[Dict[str, str]] = []
        if not self.tavily_api_key:
            return results

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": num_results,
            "include_answer": False
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("content", ""),
                            "url": item.get("url", "")
                        })
                    logger.info(f"Tavily returned {len(results)} results for '{query}'")
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}. Falling back to DuckDuckGo.")
        return results

    async def _search_ddg_http(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        Pure Python HTTP scraper for DuckDuckGo HTML endpoint.
        Requires zero binary C-extensions, fully compatible across all OS and Python versions.
        """
        results: List[Dict[str, str]] = []
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        url = "https://html.duckduckgo.com/html/"
        data = {"q": query, "b": ""}

        try:
            async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    result_divs = soup.find_all("div", class_="result")

                    for div in result_divs[:num_results]:
                        title_tag = div.find("a", class_="result__a")
                        snippet_tag = div.find("a", class_="result__snippet")
                        if not title_tag:
                            continue

                        raw_href = title_tag.get("href", "")
                        actual_url = raw_href
                        # Unpack DuckDuckGo redirect uddg parameter if present
                        if "uddg=" in raw_href:
                            parsed = urllib.parse.urlparse(raw_href)
                            params = urllib.parse.parse_qs(parsed.query)
                            if "uddg" in params:
                                actual_url = params["uddg"][0]

                        title_text = title_tag.get_text(strip=True)
                        snippet_text = snippet_tag.get_text(strip=True) if snippet_tag else ""

                        if actual_url and actual_url.startswith("http"):
                            results.append({
                                "title": title_text,
                                "snippet": snippet_text,
                                "url": actual_url
                            })
        except Exception as e:
            logger.warning(f"DuckDuckGo HTTP search error for '{query}': {e}")

        return results

    async def search_scholarships(
        self,
        degree: str,
        majors: List[str],
        funding: str,
        country: str = "Palestine"
    ) -> List[Dict[str, str]]:
        """
        Builds optimized queries and performs multi-engine asynchronous web searches.
        """
        majors_str = " ".join(majors) if majors else "Computer Science Engineering"

        query_1 = (
            f"{degree} {majors_str} {country} {funding} scholarships "
            f"\"open now\" OR \"deadline\" 2026 2027 official portal apply"
        )
        query_2 = (
            f"international scholarships for {country} students {degree} "
            f"{majors_str} fully funded 2026 2027 application"
        )

        logger.info(f"Searching web for: {country} | {degree} | {majors_str}")

        combined_results: List[Dict[str, str]] = []
        seen_urls = set()

        # 1. Try Tavily first if key is configured
        if self.tavily_api_key:
            tavily_res = await self._search_tavily(query_1, self.max_results)
            for item in tavily_res:
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    combined_results.append(item)

        # 2. Augment / Fallback with native DuckDuckGo HTTP search
        if len(combined_results) < 5:
            tasks = [
                self._search_ddg_http(query_1, self.max_results),
                self._search_ddg_http(query_2, 6)
            ]
            ddg_responses = await asyncio.gather(*tasks, return_exceptions=True)

            for res in ddg_responses:
                if isinstance(res, list):
                    for item in res:
                        url = item.get("url")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            combined_results.append(item)

        logger.info(f"Retrieved {len(combined_results)} unique search results.")
        return combined_results
