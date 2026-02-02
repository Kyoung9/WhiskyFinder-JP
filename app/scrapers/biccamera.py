import json
import re
import sys
import time
from typing import Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models.result import SearchResult


class BiccameraScraper(BaseScraper):
    name = "biccamera"
    base_url = "https://www.biccamera.com/"
    search_path = "bc/search/"
    whisky_category_url = "https://www.biccamera.com/bc/category/001/290/015/?ref=floormap"
    default_playwright_user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        category: Optional[str] = None,
        category_url: Optional[str] = None,
        max_pages: int = 1,
        timeout_seconds: int = 60,
        retry_count: int = 2,
        retry_delay_seconds: float = 1.0,
        query_encoding: str = "shift_jis",
        use_playwright: bool = True,
        playwright_browser: str = "chromium",
        playwright_headless: bool = True,
        playwright_timeout_ms: int = 45000,
        playwright_post_load_wait_ms: int = 1000,
        playwright_user_agent: Optional[str] = None,
        debug: bool = False,
        debug_output_path: Optional[str] = None,
    ):
        self.session = session or requests.Session()
        self.category = category
        self.category_url = category_url or self.whisky_category_url
        self.max_pages = max_pages
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_seconds
        self.query_encoding = query_encoding
        self.use_playwright = use_playwright
        self.playwright_browser = playwright_browser
        self.playwright_headless = playwright_headless
        self.playwright_timeout_ms = playwright_timeout_ms
        self.playwright_post_load_wait_ms = playwright_post_load_wait_ms
        self.playwright_user_agent = playwright_user_agent or self.default_playwright_user_agent
        self.debug = debug
        self.debug_output_path = debug_output_path
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.6 Safari/605.1.15"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ja,en;q=0.8",
            }
        )

    def _search_url(self, query: str, page: int = 1) -> str:
        if self.category_url:
            parsed = urlsplit(self.category_url)
            qs = parse_qs(parsed.query)
            if query:
                qs["q"] = [query]
            if page > 1:
                qs["page"] = [str(page)]
            query_str = urlencode(
                qs,
                doseq=True,
                encoding=self.query_encoding,
                errors="ignore",
            )
            return urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, query_str, parsed.fragment)
            )
        return self._search_url_basic(query, page)

    def _search_url_basic(self, query: str, page: int = 1) -> str:
        params = {"q": query}
        if self.category:
            params["category"] = self.category
        if page > 1:
            params["page"] = page
        query_str = urlencode(
            params,
            encoding=self.query_encoding,
            errors="ignore",
        )
        return f"{urljoin(self.base_url, self.search_path)}?{query_str}"

    def _parse_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"([0-9,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        last_error: Exception | None = None
        for attempt in range(self.retry_count + 1):
            try:
                response = self.session.get(url, timeout=(5, self.timeout_seconds))
                if not response.encoding:
                    response.encoding = "utf-8"
                if self.debug:
                    print(
                        f"[biccamera] {response.status_code} {url} ({len(response.text)} bytes)",
                        file=sys.stderr,
                    )
                    if self.debug_output_path:
                        try:
                            with open(self.debug_output_path, "w", encoding="utf-8") as f:
                                f.write(response.text)
                        except OSError:
                            pass
                if response.status_code in (403, 404):
                    return None
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.RequestException as exc:
                last_error = exc
                if self.debug:
                    print(f"[biccamera] request failed: {exc}", file=sys.stderr)
                if attempt >= self.retry_count:
                    break
                time.sleep(self.retry_delay_seconds)
        if last_error:
            raise last_error
        return None

    def _fetch_soup_playwright(self, page, url: str) -> Optional[BeautifulSoup]:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.playwright_timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=self.playwright_timeout_ms)
            except Exception:
                pass
            try:
                page.wait_for_selector("script[type='application/ld+json']", timeout=2000)
            except Exception:
                pass
            if self.playwright_post_load_wait_ms:
                page.wait_for_timeout(self.playwright_post_load_wait_ms)
            html = page.content()
            if self.debug:
                print(
                    f"[biccamera] playwright {url} ({len(html)} bytes)",
                    file=sys.stderr,
                )
                if self.debug_output_path:
                    try:
                        with open(self.debug_output_path, "w", encoding="utf-8") as f:
                            f.write(html)
                    except OSError:
                        pass
            return BeautifulSoup(html, "lxml")
        except Exception as exc:
            if self.debug:
                print(f"[biccamera] playwright failed: {exc}", file=sys.stderr)
            return None

    def _search_with_playwright(self, query: str) -> list[SearchResult]:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            if self.debug:
                print(f"[biccamera] playwright import failed: {exc}", file=sys.stderr)
            return []

        with sync_playwright() as p:
            if self.playwright_browser == "webkit":
                browser_type = p.webkit
            elif self.playwright_browser == "firefox":
                browser_type = p.firefox
            else:
                browser_type = p.chromium

            browser = browser_type.launch(
                headless=self.playwright_headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=self.playwright_user_agent,
                locale="ja-JP",
                viewport={"width": 1280, "height": 720},
            )
            context.set_extra_http_headers(
                {
                    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                }
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = context.new_page()
            page.route(
                "**/*",
                lambda route, request: route.abort()
                if request.resource_type in ("image", "media", "font")
                else route.continue_(),
            )

            try:
                url = self._search_url(query, page=1)
                soup = self._fetch_soup_playwright(page, url)
                if soup is None:
                    if self.category_url:
                        fallback_url = self._search_url_basic(query, page=1)
                        soup = self._fetch_soup_playwright(page, fallback_url)
                    if soup is None:
                        return []

                results = self._parse_results(soup)

                if self.max_pages <= 1:
                    return results

                if self.category_url:
                    page_urls = self._extract_page_urls(soup)
                    for page_url in page_urls[: self.max_pages - 1]:
                        page_soup = self._fetch_soup_playwright(page, page_url)
                        if page_soup is None:
                            break
                        results.extend(self._parse_results(page_soup))
                    if not results:
                        fallback_url = self._search_url_basic(query, page=1)
                        fallback_soup = self._fetch_soup_playwright(page, fallback_url)
                        if fallback_soup:
                            results = self._parse_results(fallback_soup)
                    return results

                max_page = min(self._extract_max_page(soup), self.max_pages)
                if max_page <= 1:
                    return results

                for page_num in range(2, max_page + 1):
                    page_url = self._search_url(query, page=page_num)
                    page_soup = self._fetch_soup_playwright(page, page_url)
                    if page_soup is None:
                        break
                    results.extend(self._parse_results(page_soup))

                if not results:
                    fallback_url = self._search_url_basic(query, page=1)
                    fallback_soup = self._fetch_soup_playwright(page, fallback_url)
                    if fallback_soup:
                        results = self._parse_results(fallback_soup)
                return results
            finally:
                context.close()
                browser.close()

    def _from_json_ld(self, soup: BeautifulSoup) -> list[SearchResult]:
        results: list[SearchResult] = []
        for tag in soup.find_all("script", type="application/ld+json"):
            raw = tag.string
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            def handle_item(item: dict) -> None:
                name = item.get("name") or item.get("title")
                url = item.get("url")
                offers = item.get("offers") or {}
                price = offers.get("price") if isinstance(offers, dict) else None
                if name and url and price:
                    try:
                        price_value = int(str(price).replace(",", ""))
                    except ValueError:
                        return
                    results.append(
                        SearchResult(
                            title=name,
                            price=price_value,
                            source="ビックカメラ",
                            url=urljoin(self.base_url, url),
                        )
                    )

            if isinstance(data, list):
                nodes = data
            else:
                nodes = [data]

            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if node.get("@type") == "ItemList":
                    for elem in node.get("itemListElement", []):
                        if isinstance(elem, dict):
                            item = elem.get("item") or elem
                            if isinstance(item, dict):
                                handle_item(item)
                elif node.get("@type") == "Product":
                    handle_item(node)
        return results

    def _from_links(self, soup: BeautifulSoup) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen = set()
        for link in soup.select("a[href*='/bc/item/']"):
            href = link.get("href")
            if not href:
                continue
            url = urljoin(self.base_url, href)
            if url in seen:
                continue
            seen.add(url)

            title = link.get_text(" ", strip=True)
            if not title:
                continue

            parent = link.parent
            price_text = ""
            for _ in range(3):
                if not parent:
                    break
                price_candidate = parent.get_text(" ", strip=True)
                if "円" in price_candidate or "¥" in price_candidate:
                    price_text = price_candidate
                    break
                parent = parent.parent
            price = self._parse_price(price_text)
            if price is None:
                continue

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    source="ビックカメラ",
                    url=url,
                )
            )
        return results

    def _extract_max_page(self, soup: BeautifulSoup) -> int:
        max_page = 1
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            match = re.search(r"[?&](?:page|p)=(\\d+)", href)
            if match:
                try:
                    page_num = int(match.group(1))
                    max_page = max(max_page, page_num)
                except ValueError:
                    continue
        return max_page

    def _extract_page_urls(self, soup: BeautifulSoup) -> list[str]:
        urls: list[str] = []
        seen = set()
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if not href:
                continue
            if "page=" not in href and "p=" not in href:
                continue
            full = urljoin(self.base_url, href)
            if full in seen:
                continue
            seen.add(full)
            urls.append(full)
        return urls

    def _parse_results(self, soup: BeautifulSoup) -> list[SearchResult]:
        results = self._from_json_ld(soup)
        if results:
            return results
        return self._from_links(soup)

    def search(self, query: str) -> list[SearchResult]:
        if not query:
            return []

        if self.use_playwright:
            results = self._search_with_playwright(query)
            if results:
                return results

        url = self._search_url(query, page=1)
        soup = self._fetch_soup(url)
        if soup is None:
            if self.category_url:
                fallback_url = self._search_url_basic(query, page=1)
                fallback_soup = self._fetch_soup(fallback_url)
                if fallback_soup:
                    return self._parse_results(fallback_soup)
            return []

        results = self._parse_results(soup)

        if self.max_pages <= 1:
            if not results and self.category_url:
                fallback_url = self._search_url_basic(query, page=1)
                fallback_soup = self._fetch_soup(fallback_url)
                if fallback_soup:
                    return self._parse_results(fallback_soup)
            return results

        if self.category_url:
            page_urls = self._extract_page_urls(soup)
            for page_url in page_urls[: self.max_pages - 1]:
                page_soup = self._fetch_soup(page_url)
                if page_soup is None:
                    break
                results.extend(self._parse_results(page_soup))
            if not results:
                fallback_url = self._search_url_basic(query, page=1)
                fallback_soup = self._fetch_soup(fallback_url)
                if fallback_soup:
                    results = self._parse_results(fallback_soup)
            return results

        max_page = min(self._extract_max_page(soup), self.max_pages)
        if max_page <= 1:
            return results

        for page in range(2, max_page + 1):
            page_url = self._search_url(query, page=page)
            page_soup = self._fetch_soup(page_url)
            if page_soup is None:
                break
            results.extend(self._parse_results(page_soup))

        if not results:
            fallback_url = self._search_url_basic(query, page=1)
            fallback_soup = self._fetch_soup(fallback_url)
            if fallback_soup:
                results = self._parse_results(fallback_soup)
        return results
