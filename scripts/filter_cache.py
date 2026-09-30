#!/usr/bin/env python3
"""Apply the configured AI Infra title filters to the existing DBLP cache."""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.parse
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_filters import paper_passes_filters  # noqa: E402


def _topic_keyword(topic: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        if topic.startswith(f"{urllib.parse.quote(keyword, safe='')}%20"):
            return keyword
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report removals without writing files")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    dblp = config.get("dblp", {})
    keywords = [
        value.strip()
        for value in dblp.get("keywords", [])
        if isinstance(value, str) and value.strip()
    ]
    filters = dblp.get("filters", {})
    cache_path = ROOT / "cached" / "dblp.yaml"
    cache = yaml.safe_load(cache_path.read_text(encoding="utf-8")) or {}

    removed = []
    for topic, papers in cache.items():
        keyword = _topic_keyword(topic, keywords)
        if keyword is None or not isinstance(papers, list):
            continue
        kept = []
        for paper in papers:
            title = paper.get("title", "") if isinstance(paper, dict) else ""
            if paper_passes_filters(title, keyword, filters):
                kept.append(paper)
            else:
                removed.append((keyword, title))
        cache[topic] = kept

    print(f"Removed {len(removed)} papers; kept {sum(len(v) for v in cache.values() if isinstance(v, list))}.")
    for keyword, title in removed[:20]:
        print(f"- [{keyword}] {title}")
    if len(removed) > 20:
        print(f"... and {len(removed) - 20} more")

    if not args.dry_run:
        shutil.copy2(cache_path, cache_path.with_suffix(".yaml.bak"))
        cache_path.write_text(
            yaml.safe_dump(cache, sort_keys=False, indent=2, allow_unicode=True),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
