import re
import time
from typing import Optional
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class PriceComScraper(BaseScraper):
    name = "kakaku.com"
    base_url = "https://search.kakaku.com/"
    whisky_category = "0016_0054"
    request_delay_seconds = 1.2

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        max_pages: int = 3,
    ):
        self.session = session or requests.Session()
        self.max_pages = max_pages
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "ja,en;q=0.8",
            }
        )

    def _search_url(self, query: str, page: int = 1) -> str:
        base = f"{self.base_url}{quote(query)}/?category={self.whisky_category}"
        if page <= 1:
            return base
        return f"{base}&page={page}"

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        compact = re.sub(r"\s+", "", text)
        match_any = re.search(r"([0-9,]+)", compact)
        if not match_any:
            return None
        return int(match_any.group(1).replace(",", ""))

    def _parse_source(self, item) -> str:
        quote_el = item.select_one(".p-resultItem_quote")
        if not quote_el:
            return self.name
        img = quote_el.select_one("img[alt]")
        if img and img.get("alt"):
            return img["alt"].strip()
        return quote_el.get_text(" ", strip=True) or self.name

    def _extract_final_url(self, href: str) -> str:
        if not href:
            return ""
        try:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "u" not in qs:
                return href
            first = unquote(qs["u"][0])
            parsed_first = urlparse(first)
            qs_first = parse_qs(parsed_first.query)
            if "url" in qs_first:
                return unquote(qs_first["url"][0])
            return first
        except Exception:
            return href

    def _extract_max_page(self, soup: BeautifulSoup) -> int:
        max_page = 1
        for link in soup.select(".p-pager a[href]"):
            href = link.get("href", "")
            if not href:
                continue
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "page" in qs:
                try:
                    page_num = int(qs["page"][0])
                    max_page = max(max_page, page_num)
                except (ValueError, TypeError):
                    continue
        return max_page

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        if not response.encoding:
            response.encoding = "shift_jis"
        return BeautifulSoup(response.text, "lxml")

    def _parse_results(self, soup: BeautifulSoup) -> list[SearchResult]:
        results: list[SearchResult] = []
        for item in soup.select("div.c-list1_cell.p-resultItem"):
            title_el = item.select_one(".p-item_name a")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)

            category_el = item.select_one(".p-item_category")
            if category_el:
                category = category_el.get_text(" ", strip=True)
                if category and "ウイスキー" not in category:
                    continue

            price_el = item.select_one(".p-item_price") or item.select_one(
                ".p-item_priceNum"
            )
            price_text = price_el.get_text(" ", strip=True) if price_el else ""
            price = self._parse_price(price_text)
            if price is None:
                continue

            href = title_el.get("href", "")
            final_url = self._extract_final_url(href)
            source = self._parse_source(item)

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    source=source,
                    url=final_url,
                )
            )
        return results

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        results: list[SearchResult] = []
        first_url = self._search_url(query, page=1)
        time.sleep(self.request_delay_seconds)
        soup = self._fetch_soup(first_url)
        if soup is None:
            return results

        results.extend(self._parse_results(soup))

        max_page = min(self._extract_max_page(soup), self.max_pages)
        if max_page <= 1:
            return results

        for page in range(2, max_page + 1):
            time.sleep(self.request_delay_seconds)
            page_url = self._search_url(query, page=page)
            page_soup = self._fetch_soup(page_url)
            if page_soup is None:
                break
            results.extend(self._parse_results(page_soup))

        return results
