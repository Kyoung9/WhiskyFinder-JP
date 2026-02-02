import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class ShinanoyaScraper(BaseScraper):
    name = "shinanoya"
    base_url = "https://www.shinanoya-tokyo.jp/"
    search_endpoint = "shop/shopsearch_url.html"
    whisky_category = "ct755"

    def __init__(self, session: Optional[requests.Session] = None, max_pages: int = 3):
        self.session = session or requests.Session()
        self.max_pages = max_pages
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "ja,en;q=0.8",
            }
        )

    def _resolve_search_url(self, query: str) -> Optional[str]:
        payload = {
            "keyword": query,
            "name": "",
            "price_low": "",
            "price_high": "",
            "category": self.whisky_category,
            "original_code": "",
        }
        url = urljoin(self.base_url, self.search_endpoint)
        response = self.session.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not data.get("result"):
            return None
        return urljoin(self.base_url, data.get("url", ""))

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
            response.encoding = "utf-8"
        return BeautifulSoup(response.text, "lxml")

    def _extract_max_page(self, soup: BeautifulSoup) -> int:
        max_page = 1
        for link in soup.select(".pagination a[href]"):
            href = link.get("href", "")
            if "page=" not in href:
                continue
            parsed = urlsplit(href)
            qs = parse_qs(parsed.query)
            if "page" in qs:
                try:
                    page_num = int(qs["page"][0])
                    max_page = max(max_page, page_num)
                except (ValueError, TypeError):
                    continue
        return max_page

    def _with_page(self, url: str, page: int) -> str:
        parsed = urlsplit(url)
        qs = parse_qs(parsed.query)
        qs["page"] = [str(page)]
        query = urlencode(qs, doseq=True)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        url = self._resolve_search_url(query)
        if not url:
            return []
        soup = self._fetch_soup(url)
        if soup is None:
            return []

        results: list[SearchResult] = []

        def parse_items(page_soup: BeautifulSoup) -> None:
            for item in page_soup.select(".category_itemArea_ul li"):
                title_el = item.select_one(".itemDetail .name a")
                if not title_el:
                    continue
                title = title_el.get_text(" ", strip=True)
                href = title_el.get("href", "")
                item_url = urljoin(self.base_url, href)

                price_el = item.select_one(".itemDetail .price")
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
                        source="信濃屋",
                        url=item_url,
                    )
                )

        parse_items(soup)

        max_page = min(self._extract_max_page(soup), self.max_pages)
        if max_page <= 1:
            return results

        for page in range(2, max_page + 1):
            page_url = self._with_page(url, page)
            page_soup = self._fetch_soup(page_url)
            if page_soup is None:
                break
            parse_items(page_soup)

        return results
