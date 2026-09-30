#!/usr/bin/env python3
"""Export active tracker records for review in Awesome-AIInfra."""

from __future__ import annotations

import argparse
import urllib.parse
from pathlib import Path

import yaml

from curation import classify_paper, normalize_venue


ROOT = Path(__file__).resolve().parents[1]


def configured_topics(config: dict) -> set[str]:
    dblp = config.get("dblp", {})
    keywords = dblp.get("keywords", [])
    queries = dblp.get("queries", [])
    return {
        f"{urllib.parse.quote(keyword, safe='')}%20{urllib.parse.quote(query, safe='')}"
        for keyword in keywords
        for query in queries
        if isinstance(keyword, str) and isinstance(query, str)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", action="append", type=int, help="Year to include; repeatable")
    parser.add_argument("--venue", action="append", help="Normalized venue to include; repeatable")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of records")
    parser.add_argument("--reviewed", action="store_true", help="Mark exported records as reviewed")
    parser.add_argument("--output", type=Path, default=ROOT / "candidates.yaml")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    cache = yaml.safe_load((ROOT / "cached" / "dblp.yaml").read_text(encoding="utf-8")) or {}
    active_topics = configured_topics(config)
    allowed_years = set(args.year or [])
    allowed_venues = {value.casefold() for value in (args.venue or [])}

    seen_titles: set[str] = set()
    seen_publications: set[str] = set()
    papers = []
    for topic, items in cache.items():
        if topic not in active_topics or not isinstance(items, list):
            continue
        for item in items:
            try:
                year = int(item.get("year", ""))
            except (TypeError, ValueError):
                continue
            venue, exclusion = normalize_venue(str(item.get("venue", "")))
            if exclusion or not venue:
                continue
            if allowed_years and year not in allowed_years:
                continue
            if allowed_venues and venue.casefold() not in allowed_venues:
                continue
            title = str(item.get("title", "")).strip().rstrip(".")
            publication = str(item.get("ee", "")).strip()
            title_key = " ".join(title.casefold().split())
            publication_key = publication.casefold()
            if not title or not publication or title_key in seen_titles or publication_key in seen_publications:
                continue
            seen_titles.add(title_key)
            seen_publications.add(publication_key)
            record = {
                "title": title,
                "year": year,
                "venue": venue,
                "category": classify_paper(title),
                "publication": publication,
                "source": "AIInfra-paper-update-tracker",
                "reviewed": args.reviewed,
            }
            code = str(item.get("related_code", "")).strip()
            if code:
                record["code"] = code
            papers.append(record)

    papers.sort(key=lambda item: (-item["year"], item["venue"].casefold(), item["title"].casefold()))
    if args.limit > 0:
        papers = papers[:args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump({"papers": papers}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Exported {len(papers)} candidates to {args.output}")


if __name__ == "__main__":
    main()
