import os
import re
import unicodedata

from ..models.result import SearchResult
from ..scrapers.biccamera import BiccameraScraper
from ..scrapers.mukawa import MukawaScraper
from ..scrapers.musashiya import MusashiyaScraper
from ..scrapers.pricecom import PriceComScraper
from ..scrapers.shinanoya import ShinanoyaScraper
from ..scrapers.storesjp import StoresJPScraper
from ..scrapers.yodobashi import YodobashiScraper
from ..storage.cache import TTLCache


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default

def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    value = value.strip().lower()
    if value in ("1", "true", "yes", "y", "on"):
        return True
    if value in ("0", "false", "no", "n", "off"):
        return False
    return default

def _get_str_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value

_cache = TTLCache(ttl_seconds=86400)
_scrapers = [
    PriceComScraper(max_pages=_get_int_env("WHISKYFINDER_MAX_PAGES", 3)),
    ShinanoyaScraper(max_pages=_get_int_env("WHISKYFINDER_MAX_PAGES", 3)),
    MusashiyaScraper(),
    MukawaScraper(),
    StoresJPScraper(store_slug=_get_str_env("WHISKYFINDER_STORESJP_STORE", "absinthe")),
    # BiccameraScraper(
    #     category=os.getenv("WHISKYFINDER_BICCAMERA_CATEGORY"),
    #     max_pages=_get_int_env("WHISKYFINDER_MAX_PAGES", 3),
    #     use_playwright=_get_bool_env("WHISKYFINDER_BICCAMERA_USE_PLAYWRIGHT", True),
    #     playwright_browser=os.getenv("WHISKYFINDER_BICCAMERA_PLAYWRIGHT_BROWSER", "chromium"),
    #     playwright_headless=_get_bool_env(
    #         "WHISKYFINDER_BICCAMERA_PLAYWRIGHT_HEADLESS",
    #         True,
    #     ),
    #     playwright_timeout_ms=_get_int_env(
    #         "WHISKYFINDER_BICCAMERA_PLAYWRIGHT_TIMEOUT_MS",
    #         45000,
    #     ),
    #     playwright_user_agent=os.getenv("WHISKYFINDER_BICCAMERA_PLAYWRIGHT_UA"),
    # ),
    YodobashiScraper(
        category_url=os.getenv("WHISKYFINDER_YODOBASHI_CATEGORY_URL"),
        max_pages=_get_int_env("WHISKYFINDER_MAX_PAGES", 3),
    ),
]


def _normalize_query(query: str) -> str:
    return " ".join(query.split())

def _cache_keys(query: str) -> list[str]:
    base = _normalize_query(query)
    if not base:
        return []

    variants: set[str] = {base}

    if " " not in base and "　" not in base:
        spaced = re.sub(r"([^\d\s])(\d)", r"\1 \2", base)
        if spaced != base:
            variants.add(spaced)

    for v in list(variants):
        if " " in v:
            variants.add(v.replace(" ", "　"))

    for v in list(variants):
        compact = v.replace(" ", "").replace("　", "")
        if compact:
            variants.add(compact)

    return list(variants)

def _normalize_match_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).casefold()
    normalized = "".join(
        ch
        for ch in normalized
        if unicodedata.category(ch) != "Mn"
        and unicodedata.category(ch)[0] not in ("P", "S")
    )
    normalized = re.sub(r"\s+", "", normalized)
    return normalized

def _filter_by_query(results: list[SearchResult], query: str) -> list[SearchResult]:
    needle = _normalize_match_text(query)
    if not needle:
        return results
    return [r for r in results if needle in _normalize_match_text(r.title)]

def _dedup(results: list[SearchResult]) -> list[SearchResult]:
    seen = set()
    unique = []
    for r in results:
        key = (r.title, r.source, r.price)
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def get_cached_results(query: str) -> list[SearchResult] | None:
    cache_keys = _cache_keys(query)
    for key in cache_keys:
        cached = _cache.get(key)
        if cached is not None:
            return cached
    return None


def search(query: str) -> list[SearchResult]:
    cached = get_cached_results(query)
    if cached is not None:
        return cached

    results: list[SearchResult] = []
    for scraper in _scrapers:
        results.extend(scraper.search(query))

    if _get_bool_env("WHISKYFINDER_FILTER_BY_TITLE", True):
        results = _filter_by_query(results, query)
    results = _dedup(results)
    results.sort(key=lambda r: (r.total, r.source))

    for key in _cache_keys(query):
        _cache.set(key, results)
    return results
