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
git clone https://github.com/youngfish42/FL-paper-update-tracker.git
cd FL-paper-update-tracker
pip install -r requirements.txt
```

### Local Run

```bash
cd src
python main.py run --env=dev
```

In `dev` mode the script will:
- Load the cache from `cached/dblp.yaml`
- Query DBLP for all configured `keywords × queries` combinations
- Print logs to stdout
- **Not** write to `GITHUB_ENV`

You can inspect `topic_new_items` and `msg` in the logs to preview the issue content.

Additional CLI flags:
- `--primary_only` — Compatibility mode for a single core research theme: the primary keyword scans all venues, then secondary keywords only scan venues where new papers were found. The AI Infra workflow does not use this mode because its keywords represent independent subfields.
- `--all_years` — Disable the year filter and skip abstract fetching / translation. Useful for backfilling the entire history.
- `--keyword_limit` / `--query_limit` / `--max_results` — Bound a smoke test to a small number of keywords, venues, and API results.
- `--dry_run` — Process results without writing cache changes.
- `--skip_enrichment` — Skip abstract retrieval and translation.
- `--fail_on_request_error` — Exit non-zero when DBLP cannot be reached; intended for CI smoke tests.

---

## Configuration

All behavior is controlled by `config.yaml` in the project root.

```yaml
dblp:
  url: https://dblp.org/search/publ/api?q={}&format=json&h=1000
  keywords:
    - GPU cluster
    - distributed training
    - LLM inference
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
| `dblp.url` | DBLP search API endpoint. `{}` is replaced by the fully-encoded topic query. `h=1000` requests up to 1000 hits. |
| `dblp.keywords` | List of independent title-search expressions for GPU clusters and AI infrastructure. Normal and scheduled runs scan all keyword/venue combinations. The first item only has special meaning when `--primary_only` is explicitly enabled. |
| `dblp.queries` | List of plain-text DBLP venue restrictions. The runner automatically URL-encodes each query and prepends the encoded keyword before calling the API. |
| `dblp.mails` | The first address is used as the Crossref API contact email. Additional addresses are reserved for future mail-notification features. |

### Adding a New Venue

1. Find the DBLP venue code (e.g., `venue:ICML` or `streamid:journals/pami`).
2. Append the plain query string to `dblp.queries`. For example:
   - `venue:ICML:`
   - `streamid:journals/pami:`
3. Update `scripts/convert_cache_to_md.py` if you want the new venue to appear under a specific category in `FL-Papers.md`.
4. Update `README.md` (both English and Chinese sections) to list the new venue.

---

## Workflow

This repository uses [GitHub Actions](.github/workflows/watch.yml) to run the tracker automatically.

### Triggers

| Trigger | Description |
|---------|-------------|
| **Schedule** | Every day at 00:00 UTC+8 (`cron: 0 0 * * *`) |
| **Manual** | Via `workflow_dispatch`; `smoke_test` defaults to a read-only one-query check |

### Execution Steps

1. **Checkout** – Clones the repository.
2. **Setup Python** – Installs Python 3.13.
3. **Install Dependencies** – Runs `pip install -r requirements.txt`.
4. **Run Tracker** – Executes `src/main.py` with `--env=prod`. It scans every configured `keywords × queries` combination, filters by year, deduplicates by `ee` and title, and updates `cached/dblp.yaml`. Full scanning is required because GPU clusters, inference, Kubernetes, networking, and architecture are complementary rather than secondary aliases of one keyword.
   - A manual run with `smoke_test=true` instead executes one query, caps DBLP at 10 results, skips enrichment, and does not write the cache. All mutation and notification steps are skipped.
5. **Extract Related Code** (optional) – Runs `scripts/fetch_related_code.py` to scan abstracts for GitHub repository links and backfill `related_code` fields.
6. **Fetch Missing Abstracts** (optional) – Runs `scripts/fetch_abstracts.py` to backfill empty `abstract` fields and their Chinese translations for existing papers.
   Both backfill steps ignore inactive legacy cache topics and only process the current configuration.
7. **Update FL-Papers.md** – Runs `scripts/convert_cache_to_md.py` to regenerate the categorized Markdown paper list from the updated cache.
8. **Setup Var** – Escapes the generated Markdown message for GitHub Actions.
9. **Push Done Work** – Commits `cached/dblp.yaml` and `FL-Papers.md` back to the `main` branch.
10. **Create Issue** – If new papers were found, opens a GitHub Issue using `.github/issue-template.md`.

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
│   ├── fetch_abstracts.py     # Backfill/refresh paper abstracts
│   ├── fetch_dois.py          # Backfill missing DOIs
│   ├── fetch_related_code.py  # Backfill GitHub links from abstracts
│   ├── dedup_cache_by_title.py# One-off deduplication by title
│   └── dedup_cache_global.py  # One-off global cross-topic deduplication
├── src/
│   ├── main.py                # Entry point and orchestration
│   └── utils.py               # API calls, parsing, formatting, dedup logic
├── config.yaml                # Venue list and settings
├── FL-Papers.md               # Structured Markdown output of tracked papers
├── requirements.txt           # Python dependencies
├── README.md                  # User-facing documentation
├── TECHNICAL.md               # This file
└── AGENTS.md                  # Maintenance guide for agents
```

### Key Modules

- **`src/main.py`** – Loads cache, iterates over topics, queries DBLP, filters by year, performs three-stage deduplication (by `ee`, by `title`, and global cross-topic), fetches abstracts and translations for new papers, extracts related code links, and writes new papers to `GITHUB_ENV`.
- **`src/utils.py`** – Contains `get_dblp_items` (JSON parsing), `deduplicate_items_by_ee` / `deduplicate_items_by_title` (two-stage dedup logic), `filter_items_by_year` (year window filter), `get_msg` (Markdown formatting), `fetch_abstract_for_papers` (abstract retrieval from Crossref / Semantic Scholar / arXiv / OpenAlex), `translate_abstracts_for_papers` (Chinese translation via Qwen-MT-plus), `extract_github_links` (code link extraction), `fetch_doi_for_papers` (DOI backfill), and helpers for topic short-name extraction.
- **`cached/dblp.yaml`** – YAML mapping of topic → list of paper dicts. Legacy topics may remain in this file after a domain switch, but only topics generated by the current configuration participate in deduplication and Markdown output.
- **`scripts/convert_cache_to_md.py`** – Regenerates `FL-Papers.md` from the cache using domain-specific venue and category maps.
- **`scripts/fetch_abstracts.py`** – Standalone script to backfill `abstract` fields for existing papers. Supports `--year all` and `--retry-failed`.
- **`scripts/fetch_dois.py`** – Standalone script to backfill missing `doi` fields. Supports `--year all` and `--retry-all`.
- **`scripts/fetch_related_code.py`** – Standalone script to backfill `related_code` fields by scanning abstracts for GitHub links. Supports `--year all` and `--retry-failed`.
- **`scripts/dedup_cache_by_title.py`** & **`scripts/dedup_cache_global.py`** – One-off maintenance scripts for cache deduplication.

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
  - cron: '0 0 * * *'  # Change this cron expression
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

### Backfill Related Code Links

```bash
# Process current-year papers
python scripts/fetch_related_code.py
# Process all years
python scripts/fetch_related_code.py --year all
# Retry previously failed entries
python scripts/fetch_related_code.py --retry-failed
```

### Switch to a Different Research Domain

1. Edit `config.yaml` → `dblp.keywords`.
2. Adjust `dblp.queries` to match the new domain.
3. Update `scripts/convert_cache_to_md.py`: `VENUE_MAP`, `CATEGORY_MAP`, `CATEGORY_ORDER`, and `VENUE_ORDER`.
4. Optionally reset `cached/dblp.yaml` to reclaim space. A reset is no longer required for correctness because inactive topic keys are ignored.

### Change the Message Format

Edit `src/utils.py` → `get_msg`. The function is called from `src/main.py` after merging papers by venue (`name_topic`). Each venue appears once in the issue body, with the heading plus the full paper list.

### Change the Year Window

Edit `src/utils.py` → `filter_items_by_year`:

```python
min_year = current_year - 3
max_year = current_year + 1
```

Adjust the offsets as needed.
