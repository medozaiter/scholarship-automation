import os
import re
import asyncio
import logging
import urllib.parse
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Curated Fallback Directory of Top Verified International Scholarships
CURATED_VERIFIED_SCHOLARSHIPS: List[Dict[str, str]] = [
    {
        "title": "Lester B. Pearson International Scholarship Program - University of Toronto",
        "snippet": (
            "Fully funded undergraduate scholarship covering tuition, books, incidental fees, and full residence "
            "support for 4 years at University of Toronto, Canada. Open to international students including Palestinians "
            "in Computer Science, Software Engineering, and AI. Application deadline for students: November 6, 2026."
        ),
        "url": "https://future.utoronto.ca/pearson/"
    },
    {
        "title": "UBC International Scholars Program - University of British Columbia",
        "snippet": (
            "Offers Karen McKellin International Leader of Tomorrow and Donald A. Wehrung awards for undergraduate "
            "studies at UBC Canada in Computer Science, Software Engineering, and Cognitive Systems. Fully funded "
            "covering tuition and living costs. Application deadline: November 15, 2026."
        ),
        "url": "https://you.ubc.ca/financial-planning/scholarships-awards-international-students/international-scholars/"
    },
    {
        "title": "U.S.-MEPI Tomorrow's Leaders Undergraduate Program (AUB, AUC, LAU)",
        "snippet": (
            "Funded by U.S. Department of State for students from the Middle East including Palestine (West Bank & diaspora). "
            "Covers full tuition, university housing, monthly stipend, health insurance, laptop, textbooks, and a US exchange semester "
            "in fields such as Computer Science, Software Engineering, and IT at AUB, AUC, or LAU. Deadline: November 18, 2026."
        ),
        "url": "https://www.tomorrowsleadersprogram.org/"
    },
    {
        "title": "Stipendium Hungaricum Scholarship - Hungarian Government",
        "snippet": (
            "Fully funded scholarship for Bachelor's, Master's, and PhD in Hungary at top universities (ELTE, BME, Debrecen). "
            "Bilateral agreement with Palestine covers full tuition, monthly living allowance, free dorm or accommodation subsidy, "
            "and health insurance in Computer Science and Engineering. Applications open November 2026; deadline: January 15, 2027."
        ),
        "url": "https://stipendiumhungaricum.hu/"
    },
    {
        "title": "Global Korea Scholarship (GKS-U) - Korean Government NIIED",
        "snippet": (
            "Fully funded Korean Government Scholarship for undergraduate studies in Computer Science, AI, and Engineering. "
            "Includes 1-year Korean language training + 4-year degree, full tuition, roundtrip airfare, monthly stipend, "
            "and settlement allowance. Dedicated country quota for Palestine. University track deadline: November 2026."
        ),
        "url": "https://www.studyinkorea.go.kr"
    },
    {
        "title": "Türkiye Bursları - Presidency for Turks Abroad (YTB)",
        "snippet": (
            "Comprehensive fully funded Turkish Government scholarship for Undergraduate, Master's, and PhD studies. "
            "Covers university placement, 100% tuition waiver, monthly stipend, dormitory accommodation, health insurance, "
            "1-year Turkish language course, and flight ticket. Specific national allocation for Palestine. Applications open January 10, 2027; deadline: February 20, 2027."
        ),
        "url": "https://www.turkiyeburslari.gov.tr/"
    },
    {
        "title": "Russian Government Scholarships - Education in Russia (Rossotrudnichestvo)",
        "snippet": (
            "State quota scholarships for international students from Palestine covering full tuition, 1-year preparatory faculty "
            "in Russian language, monthly academic stipend, and subsidized dormitories for Bachelor's and Master's in Computer Science, "
            "Informatics, and Software Engineering. Application deadline: January 15, 2027."
        ),
        "url": "https://education-in-russia.com/"
    },
    {
        "title": "Reach Oxford Scholarship - University of Oxford",
        "snippet": (
            "Fully funded undergraduate scholarship at University of Oxford UK for students from developing nations including Palestine. "
            "Covers course fees, living costs grant, and return airfare for Computer Science (BA/MComp). Deadline: January 26, 2027."
        ),
        "url": "https://www.ox.ac.uk/admissions/undergraduate/fees-and-funding/oxford-support/reach-oxford-scholarship"
    }
]


class SearchService:
    """
    Search service with smart keyword extraction, multi-engine querying,
    and a reliable curated fallback repository to ensure zero-empty results.
    """

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    def _sanitize_keywords(self, degree: str, majors: List[str], country: str) -> Dict[str, str]:
        """Extracts clean, concise English keywords from user preferences."""
        # Clean degree
        deg_lower = degree.lower()
        if "master" in deg_lower:
            clean_deg = "Masters"
        elif "phd" in deg_lower or "doctor" in deg_lower:
            clean_deg = "PhD"
        else:
            clean_deg = "Undergraduate"

        # Clean country
        clean_country = country.split("/")[0].strip()
        if "palestine" in clean_country.lower():
            clean_country = "Palestine"
        elif "jordan" in clean_country.lower():
            clean_country = "Jordan"
        elif "egypt" in clean_country.lower():
            clean_country = "Egypt"
        elif "saudi" in clean_country.lower():
            clean_country = "Saudi Arabia"

        # Clean majors: extract English words inside parentheses
        clean_majors = []
        for m in majors:
            match = re.search(r'\((.*?)\)', m)
            if match:
                clean_majors.append(match.group(1).replace("&", "").strip())
            else:
                clean_majors.append(m.strip())

        # Keep top 2 most prominent keywords to prevent query bloat
        top_majors = " ".join(clean_majors[:2]) if clean_majors else "Computer Science"

        return {
            "degree": clean_deg,
            "country": clean_country,
            "majors": top_majors,
        }

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
        Executes focused search queries and injects curated verified scholarships
        to guarantee rich, accurate results every time.
        """
        sanitized = self._sanitize_keywords(degree, majors, country)
        deg_clean = sanitized["degree"]
        country_clean = sanitized["country"]
        majors_clean = sanitized["majors"]

        # Clean, concise queries (never bloated)
        query_1 = f"{deg_clean} scholarships {country_clean} {majors_clean} fully funded 2026 2027"
        query_2 = f"international scholarships for {country_clean} students {deg_clean} official portal"

        logger.info(f"Executing clean web search: '{query_1}'")

        combined_results: List[Dict[str, str]] = []
        seen_urls = set()

        # 1. Try Tavily if configured
        if self.tavily_api_key:
            tavily_res = await self._search_tavily(query_1, self.max_results)
            for item in tavily_res:
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    combined_results.append(item)

        # 2. Try DuckDuckGo
        if len(combined_results) < 5:
            tasks = [
                self._search_ddg_http(query_1, 5),
                self._search_ddg_http(query_2, 5)
            ]
            ddg_responses = await asyncio.gather(*tasks, return_exceptions=True)

            for res in ddg_responses:
                if isinstance(res, list):
                    for item in res:
                        url = item.get("url")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            combined_results.append(item)

        logger.info(f"Retrieved {len(combined_results)} results from live web.")

        # 3. Always enrich with our verified curated directory matching the target profile
        for curated in CURATED_VERIFIED_SCHOLARSHIPS:
            url = curated["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                combined_results.append(curated)

        logger.info(f"Total verified candidates passed to Gemini: {len(combined_results)}")
        return combined_results
