import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

from app.scrapers.yodobashi import YodobashiScraper  # noqa: E402


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "ウイスキー"
    category_url = os.getenv("WHISKYFINDER_YODOBASHI_CATEGORY_URL")
    max_pages = _get_int_env("WHISKYFINDER_MAX_PAGES", 1)
    timeout_seconds = _get_int_env("WHISKYFINDER_YODOBASHI_TIMEOUT", 20)
    request_delay_seconds = _get_float_env("WHISKYFINDER_YODOBASHI_DELAY", 1.0)

    scraper = YodobashiScraper(
        category_url=category_url,
        max_pages=max_pages,
        timeout_seconds=timeout_seconds,
        request_delay_seconds=request_delay_seconds,
    )
    try:
        results = scraper.search(query)
    except Exception as exc:
        print(f"fetch failed: {exc}")
        return

    print(f"query: {query}")
    print(f"results: {len(results)}")
    for r in results:
        print(f"{r.title}\t{r.price}\t{r.source}\t{r.url}")


if __name__ == "__main__":
    main()
