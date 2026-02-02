import re
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class MukawaScraper(BaseScraper):
    name = "mukawa-spirit"
    base_url = "https://mukawa-spirit.com/"
    search_params = {
        "mode": "srh",
        "cid": "",
    }

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "ja,en;q=0.8",
            }
        )

    def _search_url(self, query: str) -> str:
        params = {**self.search_params, "keyword": query}
        return f"{self.base_url}?{urlencode(params, encoding='euc_jp')}"

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"([0-9,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        if not response.encoding:
            response.encoding = "euc_jp"
        return BeautifulSoup(response.text, "lxml")

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        url = self._search_url(query)
        soup = self._fetch_soup(url)
        if soup is None:
            return []

        results: list[SearchResult] = []
        for item in soup.select("li.list-product-item"):
            title_el = item.select_one(".list-product-item__ttl")
            link_el = item.select_one("a.list-product-item__link")
            price_el = item.select_one(".list-product-item__price")

            if not title_el or not link_el or not price_el:
                continue

            title = title_el.get_text(" ", strip=True)
            href = link_el.get("href", "")
            url = urljoin(self.base_url, href)

            price = self._parse_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    source="武川蒸留酒販売",
                    url=url,
                )
            )

        return results
