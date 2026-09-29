#!/usr/bin/env python3
"""
Convert cached/dblp.yaml into a structured Markdown file.

NOTE ON DOMAIN SWITCHING ──────────────────────────────────────────────
The mappings below (VENUE_MAP, CATEGORY_MAP, CATEGORY_ORDER, VENUE_ORDER)
are tailored to AI infrastructure and the
venue list in config.yaml. If you change the ``keywords`` in config.yaml
to track a different domain (e.g. diffusion, LLM), you MUST review and
update these mappings to match the new venue set and desired categories.

Quick checklist when switching domains:
1. Update ``keywords`` and ``queries`` in config.yaml.
2. Update VENUE_MAP to map DBLP raw venue names → your display names.
3. Update CATEGORY_MAP to assign each display name → a category.
4. Update CATEGORY_ORDER and VENUE_ORDER to control output ordering.
5. Optionally remove legacy cache topics to reclaim disk space; they are ignored.
───────────────────────────────────────────────────────────────────────
"""

import yaml
import urllib.parse
from pathlib import Path
from collections import defaultdict


def main():
    repo_root = Path(__file__).resolve().parent.parent
    cache_path = repo_root / "cached" / "dblp.yaml"
    output_path = repo_root / "AIInfra-Papers.md"
    config_path = repo_root / "config.yaml"

    # Load cache
    with open(cache_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    dblp_cfg = config.get("dblp", {}) if isinstance(config, dict) else {}
    keywords = dblp_cfg.get("keywords")
    if keywords is None:
        legacy_keyword = dblp_cfg.get("keyword")
        keywords = [legacy_keyword] if isinstance(legacy_keyword, str) else []
    elif isinstance(keywords, str):
        keywords = [keywords]
    elif not isinstance(keywords, list):
        keywords = []
    keywords = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
    # Keep stable lexical ordering when no valid keyword is configured.
    priority_keyword = keywords[0].lower() if keywords else ""
    queries = [
        query.strip()
        for query in dblp_cfg.get("queries", [])
        if isinstance(query, str) and query.strip()
    ]
    configured_topics = {
        f"{urllib.parse.quote(keyword, safe='')}%20{urllib.parse.quote(query, safe='')}"
        for keyword in keywords
        for query in queries
    }

    # Venue raw name -> display name
    VENUE_MAP = {
        # Systems journals
        "IEEE Trans. Parallel Distrib. Syst.": "TPDS",
        "IEEE Trans. Parallel Distributed Syst.": "TPDS",
        "ACM Trans. Comput. Syst.": "TOCS",
        # Conference aliases and co-located tracks
        "USENIX Annual Technical Conference": "USENIX ATC",
        "USENIX ATC": "USENIX ATC",
        "Symposium on Cloud Computing": "SoCC",
        "ACM Symposium on Cloud Computing": "SoCC",
        "CrossCloud@EuroSys": "EuroSys",
        "EdgeSys@EuroSys": "EuroSys",
        "EuroMLSys@EuroSys": "EuroSys",
        "Supercomputing": "SC",
    }

    # Display name -> category
    CATEGORY_MAP = {
        "MLSys": "AI / ML Systems",
        "NeurIPS": "AI / ML Systems",
        "ICML": "AI / ML Systems",
        "ICLR": "AI / ML Systems",
        "OSDI": "Cloud & Operating Systems",
        "SOSP": "Cloud & Operating Systems",
        "EuroSys": "Cloud & Operating Systems",
        "USENIX ATC": "Cloud & Operating Systems",
        "SoCC": "Cloud & Operating Systems",
        "Middleware": "Cloud & Operating Systems",
        "NSDI": "Networking & Communication",
        "SIGCOMM": "Networking & Communication",
        "SC": "High-Performance Computing",
        "HPDC": "High-Performance Computing",
        "ASPLOS": "Architecture & Accelerators",
        "ISCA": "Architecture & Accelerators",
        "MICRO": "Architecture & Accelerators",
        "HPCA": "Architecture & Accelerators",
        "TOCS": "Systems Journals",
        "TPDS": "Systems Journals",
    }

    CATEGORY_ORDER = [
        "AI / ML Systems",
        "Cloud & Operating Systems",
        "Networking & Communication",
        "High-Performance Computing",
        "Architecture & Accelerators",
        "Systems Journals",
    ]

    # Venue display order within each category (as specified by user)
    VENUE_ORDER = {
        "AI / ML Systems": ["MLSys", "NeurIPS", "ICML", "ICLR"],
        "Cloud & Operating Systems": ["OSDI", "SOSP", "EuroSys", "USENIX ATC", "SoCC", "Middleware"],
        "Networking & Communication": ["NSDI", "SIGCOMM"],
        "High-Performance Computing": ["SC", "HPDC"],
        "Architecture & Accelerators": ["ASPLOS", "ISCA", "MICRO", "HPCA"],
        "Systems Journals": ["TOCS", "TPDS"],
    }

    # Aggregate: category -> year -> venue -> [papers]
    aggregated = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    unknown_venues = set()

    for topic, papers in data.items():
        if topic not in configured_topics:
            continue
        if not isinstance(papers, list):
            continue
        for paper in papers:
            raw_venue = paper.get("venue", "").strip()
            if not raw_venue:
                continue

            venue = VENUE_MAP.get(raw_venue, raw_venue)
            category = CATEGORY_MAP.get(venue)

            if category is None:
                unknown_venues.add(raw_venue)
                continue

            year_str = paper.get("year", "")
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                continue

            aggregated[category][year][venue].append(paper)

    if unknown_venues:
        print("[WARN] Unknown venues (skipped):")
        for v in sorted(unknown_venues):
            print(f"  - {v}")

    def is_low_priority(title: str) -> bool:
        """Return True if title contains brackets or keywords like Abstract/Poster."""
        t = title.strip()
        if not t:
            return False
        has_brackets = any(c in t for c in ['(', ')', '（', '）'])
        has_keywords = any(kw in t.lower() for kw in ['abstract', 'poster'])
        return has_brackets or has_keywords

    # Build Markdown
    lines = []
    lines.append("# AI Infrastructure Papers\n")

    for category in CATEGORY_ORDER:
        if category not in aggregated:
            continue
        lines.append(f"## {category}\n")
        years = sorted(aggregated[category].keys(), reverse=True)
        for year in years:
            lines.append(f"### {year}\n")
            venue_order_map = {v: i for i, v in enumerate(VENUE_ORDER.get(category, []))}
            venues = sorted(
                aggregated[category][year].keys(),
                key=lambda v: (venue_order_map.get(v, 999), v)
            )
            for venue in venues:
                lines.append(f"#### {venue}\n")
                papers = aggregated[category][year][venue]
                papers_sorted = sorted(
                    papers,
                    key=lambda p: (
                        1 if is_low_priority(p.get("title", "")) else 0,
                        0 if priority_keyword and priority_keyword in p.get("title", "").lower() else 1,
                        p.get("title", "").lower(),
                    )
                )
                for paper in papers_sorted:
                    title = paper.get("title", "").strip()
                    ee = paper.get("ee", "").strip()
                    related_code = paper.get("related_code", "").strip()
                    # Avoid double periods if title already ends with a dot
                    suffix = "" if title.endswith(".") else "."
                    if ee:
                        if related_code:
                            lines.append(f"- {title}{suffix} [[PUB]({ee})] [[CODE]({related_code})]")
                        else:
                            lines.append(f"- {title}{suffix} [[PUB]({ee})]")
                    else:
                        lines.append(f"- {title}{suffix}")
                lines.append("")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Done! Written to {output_path}")


if __name__ == "__main__":
    main()
