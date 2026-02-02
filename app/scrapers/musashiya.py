import re
from typing import Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class MusashiyaScraper(BaseScraper):
    name = "musashiya"
    base_url = "https://store.musashiya-net.co.jp/"
    search_path = "products/list?category_id=&name="

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ja,en;q=0.8",
            }
        )

    def _search_url(self, query: str) -> str:
        return f"{self.base_url}{self.search_path}{quote_plus(query)}"

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.split())

    def _query_variants(self, query: str) -> list[str]:
        base = self._normalize_query(query)
        variants = [base]

        # If no spaces but contains digits, insert a space between text and digit blocks.
        if " " not in base and "　" not in base:
            spaced = re.sub(r"([^\d\s])(\d)", r"\1 \2", base)
            if spaced != base:
                variants.append(spaced)

        if " " in base:
            variants.append(base.replace(" ", "　"))
        if "　" in base:
            variants.append(base.replace("　", " "))

        compact = base.replace(" ", "").replace("　", "")
        if compact and compact not in variants:
            variants.append(compact)

        # Also try full-width space variant of the spaced query if present.
        for v in list(variants):
            if " " in v:
                variants.append(v.replace(" ", "　"))
        # remove duplicates while preserving order
        unique: list[str] = []
        for v in variants:
            if v not in unique:
                unique.append(v)
        return unique

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"([0-9,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        response = self.session.get(url, timeout=15)
        if response.status_code in (403, 404):
            return None
        response.raise_for_status()
        if not response.encoding:
            response.encoding = "utf-8"
        return BeautifulSoup(response.text, "lxml")

    def _parse_results(self, soup: BeautifulSoup) -> list[SearchResult]:
        results: list[SearchResult] = []
        for item in soup.select(".yak-Item"):
            title_el = item.select_one(".yak-Item__name a")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.base_url, href)

            price_el = item.select_one(".yak-Item__price")
            price = (
                self._parse_price(price_el.get_text(" ", strip=True))
                if price_el
                else None
            )
            if price is None:
                continue

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    source="武蔵屋",
                    url=url,
                )
            )
        return results

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        for q in self._query_variants(query):
            url = self._search_url(q)
            soup = self._fetch_soup(url)
            if soup is None:
                continue
            results = self._parse_results(soup)
            if results:
                return results

        return []
