#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scrapers.storesjp import StoresJPScraper


def _print_results(label: str, results: Iterable, limit: int | None) -> None:
    results = list(results)
    print(f"=== {label} results={len(results)} ===")
    count = len(results) if limit is None else min(limit, len(results))
    for item in results[:count]:
        print(f"- {item.title} | {item.price} | {item.url}")
    if limit is not None and len(results) > limit:
        print(f"... ({len(results) - limit} more)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run STORES.jp scraper with a query.")
    parser.add_argument("query", nargs="+", help="search keyword")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="max number of items to print (default: 20)",
    )
    parser.add_argument(
        "--store",
        default="absinthe",
        help="store slug for STORES.jp (default: absinthe)",
    )
    args = parser.parse_args()

    query = " ".join(args.query).strip()
    if not query:
        print("query is empty", file=sys.stderr)
        return 2

    try:
        scraper = StoresJPScraper(store_slug=args.store)
        results = scraper.search(query)
    except Exception as exc:
        print(f"[storesjp] error: {exc}", file=sys.stderr)
        results = []

    print(f"query={query}")
    print(f"store={args.store}")
    _print_results("storesjp", results, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
