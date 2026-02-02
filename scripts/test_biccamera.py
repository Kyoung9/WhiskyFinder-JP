import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

from app.scrapers.biccamera import BiccameraScraper  # noqa: E402


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "ウイスキー"
    category = os.getenv("WHISKYFINDER_BICCAMERA_CATEGORY")
    max_pages = int(os.getenv("WHISKYFINDER_MAX_PAGES", "1"))
    timeout_seconds = int(os.getenv("WHISKYFINDER_BICCAMERA_TIMEOUT", "30"))
    retry_count = int(os.getenv("WHISKYFINDER_BICCAMERA_RETRIES", "2"))
    query_encoding = os.getenv("WHISKYFINDER_BICCAMERA_QUERY_ENCODING", "shift_jis")
    use_playwright = os.getenv("WHISKYFINDER_BICCAMERA_USE_PLAYWRIGHT", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )
    playwright_browser = os.getenv("WHISKYFINDER_BICCAMERA_PLAYWRIGHT_BROWSER", "chromium")
    playwright_headless = os.getenv(
        "WHISKYFINDER_BICCAMERA_PLAYWRIGHT_HEADLESS",
        "1",
    ).strip().lower() in ("1", "true", "yes", "y", "on")
    playwright_timeout_ms = int(
        os.getenv("WHISKYFINDER_BICCAMERA_PLAYWRIGHT_TIMEOUT_MS", "45000")
    )
    playwright_user_agent = os.getenv("WHISKYFINDER_BICCAMERA_PLAYWRIGHT_UA")
    debug = os.getenv("WHISKYFINDER_BICCAMERA_DEBUG", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )
    debug_output_path = os.getenv("WHISKYFINDER_BICCAMERA_DEBUG_OUTPUT")

    scraper = BiccameraScraper(
        category=category,
        max_pages=max_pages,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
        query_encoding=query_encoding,
        use_playwright=use_playwright,
        playwright_browser=playwright_browser,
        playwright_headless=playwright_headless,
        playwright_timeout_ms=playwright_timeout_ms,
        playwright_user_agent=playwright_user_agent,
        debug=debug,
        debug_output_path=debug_output_path,
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
