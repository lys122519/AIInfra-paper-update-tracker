"""DBLP monthly-snapshot discovery, download, and streaming parsing.

The DBLP search endpoint may present an interactive verification page.  DBLP's
official recommendation for bulk workloads is to use its XML dump instead.
This module consumes the official monthly releases hosted by DROPS; it does not
attempt to solve or bypass the verification challenge.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.parse
from pathlib import Path
from typing import Iterable

import requests
from loguru import logger
from lxml import etree


COLLECTION_URL = "https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml"
STORAGE_ROOT = "https://drops.dagstuhl.de/storage/artifacts/dblp/xml"
DTD_URL = f"{STORAGE_ROOT}/2023/dblp-2023-06-28.dtd"
RELEASE_PATTERN = re.compile(r"10\.4230/dblp\.xml\.(\d{4}-\d{2}-\d{2})")
PUBLICATION_TAGS = {
    "article",
    "inproceedings",
    "proceedings",
    "book",
    "incollection",
    "phdthesis",
    "mastersthesis",
    "www",
    "data",
}
TYPE_NAMES = {
    "article": "Journal Articles",
    "inproceedings": "Conference and Workshop Papers",
    "proceedings": "Editorship",
    "book": "Books and Theses",
    "incollection": "Parts in Books or Collections",
    "phdthesis": "Books and Theses",
    "mastersthesis": "Books and Theses",
    "www": "Informal and Other Publications",
    "data": "Data and Artifacts",
}


def _user_agent(contact_email: str = "") -> str:
    contact = f" (mailto:{contact_email})" if contact_email else ""
    return f"AIInfra-paper-update-tracker/1.0{contact}"


def discover_latest_release(contact_email: str = "", timeout: int = 30) -> dict:
    """Return metadata and stable URLs for the latest official DBLP dump."""
    response = requests.get(
        COLLECTION_URL,
        headers={"User-Agent": _user_agent(contact_email)},
        timeout=timeout,
    )
    response.raise_for_status()
    releases = sorted(set(RELEASE_PATTERN.findall(response.text)))
    if not releases:
        raise RuntimeError("Could not find a DBLP XML release on the official DROPS collection page")

    release = releases[-1]
    year = release[:4]
    filename = f"dblp-{release}.xml.gz"
    download_url = f"{STORAGE_ROOT}/{year}/{filename}"
    return {
        "release": release,
        "doi": f"10.4230/dblp.xml.{release}",
        "download_url": download_url,
        "md5_url": f"{download_url}.md5",
        "dtd_url": DTD_URL,
    }


def verify_release(metadata: dict, contact_email: str = "", timeout: int = 30) -> dict:
    """HEAD-check the dump and return useful remote metadata."""
    response = requests.head(
        metadata["download_url"],
        headers={"User-Agent": _user_agent(contact_email)},
        timeout=timeout,
        allow_redirects=True,
    )
    response.raise_for_status()
    verified = dict(metadata)
    verified.update(
        {
            "content_length": int(response.headers.get("Content-Length", "0") or 0),
            "etag": response.headers.get("ETag", ""),
            "last_modified": response.headers.get("Last-Modified", ""),
        }
    )
    return verified


def _download_file(url: str, destination: Path, contact_email: str, timeout: int = 120) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with requests.get(
        url,
        headers={"User-Agent": _user_agent(contact_email)},
        timeout=(30, timeout),
        stream=True,
    ) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", "0") or 0)
        written = 0
        next_log = 256 * 1024 * 1024
        with temporary.open("wb") as output:
            for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                if not chunk:
                    continue
                output.write(chunk)
                written += len(chunk)
                if written >= next_log:
                    logger.info(f"Downloaded {written / 1024 ** 3:.2f} GiB of {total / 1024 ** 3:.2f} GiB")
                    next_log += 256 * 1024 * 1024
    temporary.replace(destination)


def _remote_md5(url: str, contact_email: str, timeout: int = 30) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": _user_agent(contact_email)},
        timeout=timeout,
    )
    response.raise_for_status()
    match = re.search(r"\b([0-9a-fA-F]{32})\b", response.text)
    if not match:
        raise RuntimeError(f"Invalid MD5 response from {url}")
    return match.group(1).lower()


def _file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)  # nosec B324 - publisher checksum only
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sync_snapshot(
    cache_dir: Path,
    contact_email: str = "",
    metadata_only: bool = False,
) -> dict:
    """Discover and optionally download the latest dump, DTD, and metadata."""
    cache_dir = Path(cache_dir)
    metadata = verify_release(discover_latest_release(contact_email), contact_email)
    if metadata_only:
        return metadata

    cache_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = cache_dir / "dblp.xml.gz"
    dtd_path = cache_dir / "dblp.dtd"
    metadata_path = cache_dir / "snapshot.json"

    current = {}
    if metadata_path.exists():
        try:
            current = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = {}

    expected_md5 = _remote_md5(metadata["md5_url"], contact_email)
    snapshot_reusable = (
        snapshot_path.exists()
        and current.get("release") == metadata["release"]
        and current.get("md5") == expected_md5
        and snapshot_path.stat().st_size == metadata.get("content_length")
    )
    if snapshot_reusable:
        logger.info(f"Using cached DBLP snapshot {metadata['release']}")
    else:
        logger.info(f"Downloading official DBLP snapshot {metadata['release']}")
        _download_file(metadata["download_url"], snapshot_path, contact_email)
        actual_md5 = _file_md5(snapshot_path)
        if actual_md5 != expected_md5:
            snapshot_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"DBLP snapshot checksum mismatch: expected {expected_md5}, got {actual_md5}"
            )
    if not dtd_path.exists():
        logger.info("Downloading the official DBLP DTD")
        _download_file(metadata["dtd_url"], dtd_path, contact_email)

    metadata.update(
        {
            "md5": expected_md5,
            "snapshot_path": str(snapshot_path.resolve()),
            "dtd_path": str(dtd_path.resolve()),
        }
    )
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def _normalise_words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def title_matches_keyword(title: str, keyword: str) -> bool:
    """Match every keyword token as a prefix of a title token.

    Prefix matching retains the project's existing truncated terms such as
    ``GPU schedul`` while keeping all matching local and deterministic.
    """
    title_words = _normalise_words(title)
    keyword_words = _normalise_words(keyword)
    return bool(keyword_words) and all(
        any(title_word.startswith(keyword_word) for title_word in title_words)
        for keyword_word in keyword_words
    )


class _LocalDtdResolver(etree.Resolver):
    def __init__(self, dtd_path: Path):
        super().__init__()
        self.dtd_path = str(Path(dtd_path).resolve())

    def resolve(self, url, public_id, context):  # noqa: D401 - lxml callback signature
        if url.endswith("dblp.dtd") or "dblp-" in url and url.endswith(".dtd"):
            return self.resolve_filename(self.dtd_path, context)
        return None


def _element_text(element, child_name: str) -> str:
    child = element.find(child_name)
    return "" if child is None else "".join(child.itertext()).strip()


def _record_to_item(element) -> dict:
    key = element.get("key", "")
    authors = ["".join(author.itertext()).strip() for author in element.findall("author")]
    if not authors:
        authors = ["".join(editor.itertext()).strip() for editor in element.findall("editor")]

    ee_elements = element.findall("ee")
    ee_values = ["".join(value.itertext()).strip() for value in ee_elements]
    ee_values = [value for value in ee_values if value]
    doi = ""
    for value in ee_values:
        match = re.search(r"(?:https?://doi\.org/|doi:)(10\.[^\s]+)", value, re.IGNORECASE)
        if match:
            doi = match.group(1).rstrip(".,;:)]}")
            break

    venue = _element_text(element, "booktitle") or _element_text(element, "journal")
    access = "open" if any(value.get("type") == "oa" for value in ee_elements) else ""
    return {
        "author": ", ".join(value for value in authors if value),
        "title": _element_text(element, "title"),
        "venue": venue,
        "year": _element_text(element, "year"),
        "type": TYPE_NAMES.get(element.tag, ""),
        "access": access,
        "key": key,
        "doi": doi,
        "ee": ee_values[0] if ee_values else "",
        "url": f"https://dblp.org/rec/{urllib.parse.quote(key, safe='/')}" if key else "",
        "abstract": "",
        "abstract_cn": "",
        "related_code": "",
    }


def load_snapshot_items_by_topic(
    snapshot_path: Path,
    dtd_path: Path | None,
    keywords: Iterable[str],
    queries: Iterable[str],
    query_key_prefixes: dict[str, str],
    min_year: int | None = None,
    max_year: int | None = None,
    max_results: int = 0,
) -> dict[str, list[dict]]:
    """Stream one XML dump and distribute matching records into topic lists."""
    keywords = list(keywords)
    queries = list(queries)
    missing = [query for query in queries if query not in query_key_prefixes]
    if missing:
        raise ValueError(f"Missing dblp.snapshot.query_key_prefixes entries for: {missing}")

    topics = {
        (keyword, query): (
            f"{urllib.parse.quote(keyword, safe='')}%20{urllib.parse.quote(query, safe='')}"
        )
        for keyword in keywords
        for query in queries
    }
    results = {topic: [] for topic in topics.values()}
    query_by_key_prefix = {
        prefix.rstrip("/"): query
        for query, prefix in query_key_prefixes.items()
        if query in queries
    }

    parser = etree.XMLPullParser(
        events=("end",),
        tag=tuple(PUBLICATION_TAGS),
        load_dtd=bool(dtd_path),
        resolve_entities=bool(dtd_path),
        no_network=True,
        huge_tree=True,
    )
    if dtd_path:
        parser.resolvers.add(_LocalDtdResolver(Path(dtd_path)))

    opener = gzip.open if str(snapshot_path).endswith(".gz") else open
    matched_records = 0
    with opener(snapshot_path, "rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            parser.feed(chunk)
            for _, element in parser.read_events():
                key = element.get("key", "")
                key_parts = key.split("/", 2)
                key_prefix = "/".join(key_parts[:2]) if len(key_parts) >= 2 else ""
                query = query_by_key_prefix.get(key_prefix)
                if query:
                    year_text = _element_text(element, "year")
                    try:
                        year = int(year_text)
                    except ValueError:
                        year = None
                    in_year_range = year is not None and (
                        (min_year is None or year >= min_year)
                        and (max_year is None or year <= max_year)
                    )
                    if in_year_range:
                        title = _element_text(element, "title")
                        matching_keywords = [
                            keyword for keyword in keywords if title_matches_keyword(title, keyword)
                        ]
                        if matching_keywords:
                            item = _record_to_item(element)
                            for keyword in matching_keywords:
                                topic = topics[(keyword, query)]
                                if max_results <= 0 or len(results[topic]) < max_results:
                                    results[topic].append(dict(item))
                            matched_records += 1

                element.clear()
                parent = element.getparent()
                if parent is not None:
                    while element.getprevious() is not None:
                        del parent[0]
    parser.close()
    logger.info(f"Matched {matched_records} DBLP records from local snapshot")
    return results
