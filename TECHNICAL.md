# Technical Details

> Deployment, configuration, and workflow documentation for maintainers and developers.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Workflow](#workflow)
- [Project Structure](#project-structure)
- [Common Tasks](#common-tasks)

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/lys122519/AIInfra-paper-update-tracker.git
cd AIInfra-paper-update-tracker
pip install -r requirements.txt
python scripts/sync_dblp_snapshot.py
```

### Local Run

```bash
cd src
python main.py run --env=dev
```

In `dev` mode the script will:
- Load the cache from `cached/dblp.yaml`
- Stream the local official DBLP XML snapshot once for all configured `keywords × queries` combinations
- Print logs to stdout
- **Not** write to `GITHUB_ENV`

You can inspect `topic_new_items` and `msg` in the logs to preview the issue content.

Additional CLI flags:
- `--all_years` — Disable the year filter and skip abstract fetching / translation. Useful for backfilling the entire history.
- `--keyword_limit` / `--query_limit` / `--max_results` — Bound local snapshot processing to a small number of keywords, venues, and results per topic.
- `--dry_run` — Process results without writing cache changes.
- `--skip_enrichment` — Skip abstract retrieval and translation.

---

## Configuration

All behavior is controlled by `config.yaml` in the project root.

```yaml
dblp:
  source: snapshot
  snapshot:
    path: .cache/dblp/dblp.xml.gz
    dtd_path: .cache/dblp/dblp.dtd
    query_key_prefixes:
      "venue:MLSys:": conf/mlsys
      "streamid:conf/sc:": conf/sc
  keywords:
    - AI infrastructure
    - distributed training
    - LLM inference
  filters:
    exclude_title_keywords:
      - federated
      - FedAvg
    require_any_by_keyword:
      quantization:
        - inference
        - training
        - hardware
    - Kubernetes
    - ...
  queries:
    - "venue:MLSys:"
    - "venue:OSDI:"
    - "streamid:conf/sc:"
    # ... add more queries here
  mails:
    - "im.young@foxmail.com"
```

### Fields

| Field | Description |
|-------|-------------|
| `dblp.source` | Must be `snapshot` (default): reads the official monthly dump. The legacy search-API mode has been removed. |
| `dblp.snapshot.path` / `dtd_path` | Local files created by `scripts/sync_dblp_snapshot.py`; both live under the ignored `.cache/` directory. |
| `dblp.snapshot.query_key_prefixes` | Maps each configured query label to a stable DBLP record-key prefix, such as `venue:MLSys:` → `conf/mlsys`. |
| `dblp.keywords` | List of independent title-search expressions for AI infrastructure. Every run scans all keyword/venue combinations. |
| `dblp.filters.exclude_title_keywords` | Case-insensitive title expressions that are always rejected. Tokens use prefix matching, so stems such as `federat` are supported. |
| `dblp.filters.require_any_by_keyword` | Optional positive context rules for broad keywords. A matching paper must contain at least one listed expression in its title. |
| `dblp.queries` | List of plain-text venue labels. The runner combines them with keywords only to preserve the existing encoded cache keys and display links. |
| `dblp.mails` | The first address is used as the Crossref API contact email. Additional addresses are reserved for future mail-notification features. |

### Adding a New Venue

1. Find the DBLP venue code and record-key prefix (for example `venue:ICML:` and `conf/icml`).
2. Append the plain query string to `dblp.queries` and add the same query to `dblp.snapshot.query_key_prefixes`.
   - `venue:ICML:`
   - `streamid:journals/pami:`
3. Update `scripts/convert_cache_to_md.py` if you want the new venue to appear under a specific category in `AIInfra-Papers.md`.
4. Update `README.md` (both English and Chinese sections) to list the new venue.

---

## Workflow

This repository uses [GitHub Actions](.github/workflows/watch.yml) to run the tracker automatically.

### Triggers

| Trigger | Description |
|---------|-------------|
| **Schedule** | Twice per month, on days 6 and 20 at 01:15 UTC (`cron: 15 1 6,20 * *`) |
| **Manual** | Via `workflow_dispatch`; `smoke_test` defaults to release discovery plus local parser tests |

### Execution Steps

1. **Checkout** – Clones the repository.
2. **Setup Python** – Installs Python 3.13.
3. **Install Dependencies** – Runs `pip install -r requirements.txt`.
4. **Discover Snapshot** – Resolves the newest release from the official DROPS collection and validates its download URL with HEAD.
5. **Restore / Download Snapshot** – Reuses an Actions cache keyed by the exact release date, or downloads the gzip dump, verifies its publisher MD5, and downloads the official DTD.
6. **Run Tracker** – Streams the XML once, filters records by key prefix, year, title keywords, exclusions, and required infrastructure context, then deduplicates and updates `cached/dblp.yaml`.
   - A manual run with `smoke_test=true` stops after release discovery and bundled parser tests. All large downloads, mutations, and notifications are skipped.
7. **Fetch Missing Abstracts** (optional) – Runs `scripts/fetch_abstracts.py` to retry empty `abstract` fields for existing papers, extracting `related_code` GitHub links and Chinese translations along the way.
   This step ignores inactive legacy cache topics and only processes the current configuration.
8. **Update AIInfra-Papers.md** – Runs `scripts/convert_cache_to_md.py` to regenerate the categorized Markdown paper list from the updated cache.
9. **Push / Create Issue** – Commits generated data and opens an Issue when new papers exist.

### Issue Format

The issue title follows this pattern:

```
Paper Update [Venue1, Venue2, ...] @ YYYY-MM-DD
```

The issue body contains:
- A summary header for each venue with new papers (e.g., `VenueName [+3]`)
- An unordered list of paper titles with `[PUB]` hyperlinks pointing to the DBLP `ee` field
- When a `related_code` field is present, an additional `[CODE]` hyperlink is appended after `[PUB]`

---

## Project Structure

```
.
├── .github/
│   ├── workflows/
│   │   └── watch.yml          # GitHub Actions workflow
│   └── issue-template.md      # Issue template (Nunjucks)
├── cached/
│   └── dblp.yaml              # Persistent cache of reported papers
├── scripts/
│   ├── convert_cache_to_md.py # Converts cache to structured Markdown
│   ├── curation.py            # Shared venue policy and category helpers
│   ├── export_candidates.py   # Exports review batches for Awesome-AIInfra
│   ├── fetch_abstracts.py     # Backfill/refresh paper abstracts
│   ├── fetch_dois.py          # Backfill missing DOIs
│   ├── filter_cache.py        # Apply current title filters to the cache
│   └── sync_dblp_snapshot.py  # Discover/download/check official DBLP dump
├── src/
│   ├── main.py                # Entry point and orchestration
│   ├── dblp_snapshot.py       # DROPS sync metadata and streaming XML parser
│   ├── paper_filters.py       # Title exclusions and context rules
│   └── utils.py               # Metadata API calls, formatting, dedup logic
├── config.yaml                # Venue list and settings
├── AIInfra-Papers.md          # Structured Markdown output of tracked papers
├── requirements.txt           # Python dependencies
├── README.md                  # User-facing documentation
├── TECHNICAL.md               # This file
└── AGENTS.md                  # Maintenance guide for agents
```

### Key Modules

- **`src/main.py`** – Loads cache and one locally parsed snapshot result, then performs three-stage deduplication, enrichment, notification formatting, and cache updates.
- **`src/dblp_snapshot.py`** – Discovers official DROPS releases, verifies downloads, and stream-parses gzip XML with its local DTD while keeping memory bounded.
- **`src/paper_filters.py`** – Applies configurable global title exclusions and per-keyword infrastructure-context requirements.
- **`src/utils.py`** – Contains `deduplicate_items_by_ee` / `deduplicate_items_by_title` (two-stage dedup logic), `get_configured_keywords` / `get_configured_topics` (config parsing), `get_msg` (Markdown formatting), `fetch_abstract_for_papers` (abstract retrieval from Crossref / Semantic Scholar / arXiv / OpenAlex), `translate_abstracts_for_papers` (Chinese translation via Qwen-MT-plus), `extract_github_links` (code link extraction), `fetch_doi_for_papers` (DOI backfill), and helpers for topic short-name extraction.
- **`cached/dblp.yaml`** – YAML mapping of topic → list of paper dicts. Legacy topics may remain in this file after a domain switch, but only topics generated by the current configuration participate in deduplication and Markdown output.
- **`scripts/convert_cache_to_md.py`** – Regenerates `AIInfra-Papers.md` from the cache using domain-specific venue and category maps.
- **`scripts/curation.py`** – Normalizes venue variants, explicitly excludes secondary tracks, and assigns initial curation categories.
- **`scripts/export_candidates.py`** – Exports selected years and normalized venues as a structured YAML review batch for Awesome-AIInfra.
- **`scripts/filter_cache.py`** – Applies the current title filters to existing cache entries. Use `--dry-run` to preview removals.
- **`scripts/fetch_abstracts.py`** – Standalone script to backfill `abstract` fields for existing papers. Supports `--year all` and `--retry-failed`.
- **`scripts/fetch_dois.py`** – Standalone script to backfill missing `doi` fields. Supports `--year all` and `--retry-all`.

---

## Common Tasks

### Reset the Cache

If the cache becomes corrupted or you want to re-report all papers:

```bash
rm cached/dblp.yaml
```

The next run will treat every paper as new and recreate the cache.

### Change the Issue Schedule

Edit `.github/workflows/watch.yml`:

```yaml
schedule:
  - cron: '15 1 6,20 * *'
```

### Backfill Abstracts

```bash
# Process current-year papers (default)
python scripts/fetch_abstracts.py
# Process all years
python scripts/fetch_abstracts.py --year all
# Retry previously failed entries
python scripts/fetch_abstracts.py --retry-failed
```

### Backfill DOIs

```bash
# Process current-year papers with missing DOI
python scripts/fetch_dois.py
# Process all years
python scripts/fetch_dois.py --year all
# Re-fetch for all papers
python scripts/fetch_dois.py --retry-all
```

### Switch to a Different Research Domain

1. Edit `config.yaml` → `dblp.keywords`.
2. Adjust `dblp.queries` to match the new domain.
3. Update `scripts/convert_cache_to_md.py`: `VENUE_MAP`, `CATEGORY_MAP`, `CATEGORY_ORDER`, and `VENUE_ORDER`.
4. Optionally reset `cached/dblp.yaml` to reclaim space. A reset is no longer required for correctness because inactive topic keys are ignored.

### Export an Awesome-AIInfra Review Batch

```bash
python scripts/export_candidates.py \
  --year 2025 \
  --venue MLSys \
  --venue OSDI \
  --output candidates.yaml
```

Main proceedings, Findings, and industry tracks are eligible. Workshops, demos, posters, tutorials, student tracks, companion volumes, and position papers are excluded by `scripts/curation.py`. Exported records default to `reviewed: false`; only use `--reviewed` after manual review.

### Change the Message Format

Edit `src/utils.py` → `get_msg`. The function is called from `src/main.py` after merging papers by venue (`name_topic`). Each venue appears once in the issue body, with the heading plus the full paper list.

### Change the Year Window

Edit `src/main.py`, where the window is passed to the snapshot parser:

```python
min_year=None if all_years else current_year - 3,
max_year=None if all_years else current_year + 1,
```

Adjust the offsets as needed.
