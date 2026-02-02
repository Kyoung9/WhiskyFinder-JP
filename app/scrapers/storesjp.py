import re
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class StoresJPScraper(BaseScraper):
    name = "stores.jp"
    base_url = "https://stores.jp"
    search_path = "/search"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        store_slug: str = "absinthe",
        timeout_seconds: int = 15,
    ):
        self.session = session or requests.Session()
        self.store_slug = store_slug
        self.timeout_seconds = timeout_seconds
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "ja,en;q=0.8",
            }
        )

    def _search_url(self, query: str) -> str:
        params = {"q": query}
        if self.store_slug:
            params["store"] = self.store_slug
        return f"{self.base_url}{self.search_path}?{urlencode(params)}"

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"([0-9,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        response = self.session.get(url, timeout=self.timeout_seconds)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        if not response.encoding:
            response.encoding = "utf-8"
        return BeautifulSoup(response.text, "lxml")

    def _parse_results(self, soup: BeautifulSoup) -> list[SearchResult]:
        results: list[SearchResult] = []
        for item in soup.select("article.feed_list"):
            title_el = item.select_one(".feed_list_name_main a")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)

            href = title_el.get("href", "")
            url = urljoin(self.base_url, href)

            price_el = item.select_one(".feed_item_price_range") or item.select_one(
                ".feed_item_price"
            )
            price_text = price_el.get_text(" ", strip=True) if price_el else ""
            price = self._parse_price(price_text)
            if price is None:
                continue

            source_el = item.select_one(".feed_list_name_sub a")
            source = (
                source_el.get_text(" ", strip=True)
                if source_el
                else self.name
            )

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    source=source,
                    url=url,
                )
            )

        return results

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        url = self._search_url(query)
        soup = self._fetch_soup(url)
        if soup is None:
            return []

        return self._parse_results(soup)
