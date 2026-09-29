"""Discover and download the latest official DBLP XML snapshot."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dblp_snapshot import sync_snapshot  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true", help="discover and HEAD-check only")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "dblp")
    parser.add_argument("--github-output", type=Path, help="append release metadata for GitHub Actions")
    parser.add_argument("--contact-email", default=os.getenv("DBLP_CONTACT_EMAIL", ""))
    args = parser.parse_args()

    metadata = sync_snapshot(
        cache_dir=args.cache_dir,
        contact_email=args.contact_email,
        metadata_only=args.metadata_only,
    )
    size_gib = metadata.get("content_length", 0) / 1024 ** 3
    print(f"DBLP snapshot: {metadata['release']} ({size_gib:.2f} GiB)")
    print(f"DOI: https://doi.org/{metadata['doi']}")

    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"release={metadata['release']}\n")
            output.write(f"doi={metadata['doi']}\n")


if __name__ == "__main__":
    main()
