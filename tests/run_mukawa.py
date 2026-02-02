#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scrapers.mukawa import MukawaScraper
from app.scrapers.shinanoya import ShinanoyaScraper


def _print_results(label: str, results: Iterable, limit: int | None) -> None:
    results = list(results)
    print(f"=== {label} results={len(results)} ===")
    count = len(results) if limit is None else min(limit, len(results))
    for item in results[:count]:
        print(f"- {item.title} | {item.price} | {item.url}")
    if limit is not None and len(results) > limit:
        print(f"... ({len(results) - limit} more)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Mukawa and Shinanoya scrapers with a query."
    )
    parser.add_argument("query", nargs="+", help="search keyword")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="max number of items to print per scraper (default: 20)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="max pages for Shinanoya (default: 3)",
    )
    args = parser.parse_args()

    query = " ".join(args.query).strip()
    if not query:
        print("query is empty", file=sys.stderr)
        return 2

    try:
        mukawa = MukawaScraper()
        mukawa_results = mukawa.search(query)
    except Exception as exc:
        print(f"[mukawa] error: {exc}", file=sys.stderr)
        mukawa_results = []

    try:
        shinanoya = ShinanoyaScraper(max_pages=args.max_pages)
        shinanoya_results = shinanoya.search(query)
    except Exception as exc:
        print(f"[shinanoya] error: {exc}", file=sys.stderr)
        shinanoya_results = []

    print(f"query={query}")
    _print_results("mukawa", mukawa_results, args.limit)
    _print_results("shinanoya", shinanoya_results, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
