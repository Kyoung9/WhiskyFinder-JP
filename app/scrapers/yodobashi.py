import re
import time
from typing import Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class YodobashiScraper(BaseScraper):
    name = "yodobashi"
    base_url = "https://www.yodobashi.com/"
    whisky_category_url = "https://www.yodobashi.com/category/157851/165152/165173/"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        category_url: Optional[str] = None,
        max_pages: int = 3,
        timeout_seconds: int = 20,
        request_delay_seconds: float = 1.0,
    ):
        self.session = session or requests.Session()
        self.category_url = category_url or self.whisky_category_url
        self.max_pages = max_pages
        self.timeout_seconds = timeout_seconds
        self.request_delay_seconds = request_delay_seconds
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

    def _search_url(self, query: str, page: int = 1) -> str:
        parsed = urlsplit(self.category_url)
        path = parsed.path or "/"
        if not path.endswith("/"):
            path += "/"
        path = re.sub(r"/p\d+/$", "/", path)
        if page > 1:
            path = path.rstrip("/")
            path = f"{path}/p{page}/"
        qs = parse_qs(parsed.query)
        if query:
            qs["word"] = [query]
        query_str = urlencode(qs, doseq=True)
        return urlunsplit((parsed.scheme, parsed.netloc, path, query_str, parsed.fragment))

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"([0-9,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        response = self.session.get(url, timeout=self.timeout_seconds)
        if response.status_code in (403, 404):
            return None
        response.raise_for_status()
        if not response.encoding:
            response.encoding = "utf-8"
        return BeautifulSoup(response.text, "lxml")

    def _parse_results(self, soup: BeautifulSoup) -> list[SearchResult]:
        results: list[SearchResult] = []
        for item in soup.select("div.srcResultItem_block.pListBlock"):
            title_el = item.select_one(".pName")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)

            link_el = item.select_one("a[href^='/product/'], a[href*='/product/']")
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href:
                continue
            url = urljoin(self.base_url, href)

            price_el = item.select_one(".productPrice")
            price_text = price_el.get_text(" ", strip=True) if price_el else ""
            price = self._parse_price(price_text)
            if price is None:
                continue

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    source="ヨドバシ.com",
                    url=url,
                )
            )
        return results

    def _extract_max_page(self, soup: BeautifulSoup) -> int:
        max_page = 1
        for link in soup.select("div.pagn a[href], div.pgBtmBox a[href], div.pgTopBox a[href]"):
            href = link.get("href", "")
            match = re.search(r"/p(\d+)/", href)
            if match:
                try:
                    page_num = int(match.group(1))
                    max_page = max(max_page, page_num)
                except ValueError:
                    continue
        return max_page

    def _sleep(self) -> None:
        if self.request_delay_seconds > 0:
            time.sleep(self.request_delay_seconds)

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        self._sleep()
        first_url = self._search_url(query, page=1)
        soup = self._fetch_soup(first_url)
        if soup is None:
            return []

        results: list[SearchResult] = []
        results.extend(self._parse_results(soup))

        max_page = min(self._extract_max_page(soup), self.max_pages)
        if max_page <= 1:
            return results

        for page in range(2, max_page + 1):
            self._sleep()
            page_url = self._search_url(query, page=page)
            page_soup = self._fetch_soup(page_url)
            if page_soup is None:
                break
            results.extend(self._parse_results(page_soup))

        return results
