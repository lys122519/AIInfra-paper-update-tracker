# Agent Guidance for AIInfra-paper-update-tracker

> This file is intended for automated coding agents (and human maintainers) who need to understand, modify, or extend the project. Keep it up-to-date whenever architecture, logic, or conventions change.

## Project Overview

**AIInfra-paper-update-tracker** is an automated AI Infrastructure paper tracker. It follows AI/ML systems, NLP and language models, retrieval, multimodal learning, cloud and operating systems, networking, HPC, computer architecture, and related journals.

### High-Level Workflow
1. GitHub Actions updates the tracker twice per month, on days 3 and 17 at 01:15 UTC (`15 1 3,17 * *`), and supports manual dispatch. Manual runs default to a read-only release check plus bundled parser tests; they do not download the large dump or mutate the repository.
2. `scripts/sync_dblp_snapshot.py` discovers the newest official DBLP XML release on DROPS, downloads and MD5-verifies it on full runs, and stores the dump plus DTD under ignored `.cache/dblp/`. Actions caches this directory by exact release date.
3. `src/dblp_snapshot.py` streams the gzip XML once and locally filters by year, DBLP record-key prefix, title keyword, and the rules in `dblp.filters`. `src/main.py` consumes the resulting URL-encoded topic mapping, preserving the existing cache and Issue format.
4. Extracted paper metadata is **filtered by year** (last 3 years + next 1 year) and **deduplicated by `ee` field**.
5. New papers (not yet in `cached/dblp.yaml`) are collected, formatted as Markdown, and written to the `GITHUB_ENV` variable `MSG`.
6. `scripts/convert_cache_to_md.py` regenerates `AIInfra-Papers.md` from the updated cache.
7. If new papers exist, the action `JasonEtco/create-an-issue@v2` creates a GitHub Issue using `.github/issue-template.md`.
8. Both `cached/dblp.yaml` and `AIInfra-Papers.md` are committed back to the repo so that subsequent runs know what has already been reported.

## Tech Stack

- **Language**: Python 3.13
- **Core Dependencies** (see `requirements.txt`):
  - `fire` – CLI scaffolding
  - `requests` – official snapshot discovery/download plus metadata APIs
  - `lxml` – bounded-memory XML parsing with the official local DTD
  - `loguru` – structured logging
  - `pyyaml` – cache read/write
- **CI/CD**: GitHub Actions (Ubuntu runner)
- **License**: Apache 2.0

## Directory Structure

```
.
├── .github/
│   ├── workflows/watch.yml          # GitHub Actions workflow definition
│   └── issue-template.md            # Nunjucks template for auto-created issues
├── cached/
│   └── dblp.yaml                    # Persistent cache of already-reported papers
├── scripts/
│   ├── convert_cache_to_md.py       # Converts cache to structured Markdown (domain-specific maps)
│   ├── curation.py                  # Shared venue policy and curation categories
│   ├── export_candidates.py         # Export Awesome-AIInfra review batches
│   ├── fetch_abstracts.py           # Backfill/refresh paper abstracts via external APIs
│   ├── fetch_dois.py                # Backfill missing DOIs via DBLP / Crossref / Semantic Scholar
│   ├── sync_dblp_snapshot.py        # Discover, verify, and download official XML releases
│   ├── dedup_cache_by_title.py      # Deduplicate cache entries by title
│   ├── dedup_cache_global.py        # Global cross-topic deduplication for the cache
│   └── filter_cache.py              # Apply current title filters to existing cache data
├── src/
│   ├── main.py                      # Entry point: consumes local topic results and updates the cache
│   ├── dblp_snapshot.py             # DROPS release sync and streaming local XML filtering
│   ├── paper_filters.py             # Configurable title exclusions and context rules
│   └── utils.py                     # Helper functions: API call, parsing, formatting, dedup
├── config.yaml                      # keyword, plain queries (venues), and mail targets
├── AIInfra-Papers.md                # Structured Markdown output of all tracked papers
├── requirements.txt                 # Python dependencies
├── README.md                        # Human-facing documentation (EN + CN)
├── TECHNICAL.md                     # Deployment and configuration guide
└── AGENTS.md                        # This file
```

## Key Logic & Conventions

### 1. Year Filtering
- Location: `src/main.py` (calls `filter_items_by_year` in `src/utils.py`)
- Rule: Only papers whose `year` falls in `[current_year - 3, current_year + 1]` are kept.
- Example: In 2026, valid years are 2023–2027.
- **Agent Note**: If you change this window, update both the implementation **and** this document.

### 2. Deduplication
- Location: `src/utils.py` + `src/main.py`
- **Three-stage dedup**:
  1. `deduplicate_items_by_ee` (per-topic) — Within a single DBLP query result, papers with identical `ee` are deduplicated. Rationale: DBLP sometimes returns multiple records for the same paper with minor author-name differences (e.g., `Ming Hu 0003` vs `Ming Hu`).
  2. `deduplicate_items_by_title` (per-topic) — Within a single query result, papers with identical `title` are also deduplicated. Rationale: DBLP may list the same paper multiple times under different `ee` URLs (e.g., preprint vs. proceedings version).
  3. **Global cross-topic dedup** (in `main.py`) — A paper that has already been cached under any currently configured topic is skipped when processing subsequent topics. Inactive legacy topic keys are deliberately excluded, so a domain switch can retain old cache data without contaminating or suppressing current results.
- **Agent Note**: Do **not** switch back to full-dict comparison (`item not in cached_items`) unless you also normalize author names.

### 3. Cache Format (`cached/dblp.yaml`)
- Top-level keys: URL-encoded DBLP search topics (e.g., `AI%20infrastructure%20venue%3AMLSys%3A:`).
- Each key maps to a list of paper dicts with fields: `author`, `title`, `venue`, `year`, `type`, `access`, `key`, `doi`, `ee`, `url`, `abstract`, `abstract_cn`, `related_code`.
  - `abstract`  may be empty for legacy entries; use `scripts/fetch_abstracts.py` to backfill it.
  - `abstract_cn` is the Chinese translation of `abstract`, auto-generated via Qwen-MT-plus.
  - `related_code` stores the first GitHub repository URL detected in `abstract` (or empty string if none).
- The file is overwritten after every successful run.
- Legacy topic keys from earlier research domains may remain in the file. The tracker, Markdown converter, and metadata backfill scripts only process topics generated by the current `keywords × queries` configuration.
- **Agent Note**: If you add new fields to the paper dict, ensure backward compatibility; old cache entries missing the new field should be handled gracefully.

### 4. Message Formatting (`get_msg`)
- Location: `src/utils.py`
- `get_msg` generates a Markdown block for a single venue: heading with `[+N]` count plus an unordered list of papers in the form:
  ```markdown
  - {title}. [PUB]({ee})
  ```
- `src/main.py` collects new papers from **all keyword + query combinations**, then **merges them by venue** (`name_topic`, e.g. `journals/ml`). Papers found under the same venue by different keywords are combined into a single block, deduplicated by `ee`/`title`, and counted together.
- `get_topic_short_name` extracts the venue short name (the segment after the last `/`, or the whole name if no `/`) from a topic URL. Used for the Issue title.
- `format_title_topics` joins short names with `, ` and truncates to ≤80 characters, appending `等N个` when truncated.

### 5. Issue Title Construction
- Template: `.github/issue-template.md`
- Title: `Paper Update [{{ env.ISSUE_TITLE_TOPICS }}] @ {{ date | date('YYYY-MM-DD') }}`
- The environment variable `ISSUE_TITLE_TOPICS` is populated in `src/main.py` and passed through the workflow `env` block.

### 6. Configuration (`config.yaml`)
```yaml
dblp:
  source: snapshot
  snapshot:
    path: .cache/dblp/dblp.xml.gz
    dtd_path: .cache/dblp/dblp.dtd
    query_key_prefixes:
      "venue:MLSys:": conf/mlsys
  url: https://dblp.org/search/publ/api?q={}&format=json&h=1000
  keywords:
    - AI infrastructure
    - distributed training
    - LLM inference
    - Kubernetes
    - ...
  queries:
    - "venue:MLSys:"
    - "venue:OSDI:"
    - ...
  mails:
    - "im.young@foxmail.com"
```
- `keywords`: Independent AI-Infra title-search expressions. Automatic and normal manual runs scan all `keywords × queries` combinations because the topics are complementary.
  - The optional `primary_only=True` compatibility mode is only appropriate when the remaining keywords are aliases of one primary theme. Do not enable it for the current multi-theme configuration.
- `source`: `snapshot` is the normal mode. `api` is retained only for legacy or small-workload compatibility.
- `snapshot.query_key_prefixes`: Every configured query must map to a stable XML record-key prefix. Local filtering uses this mapping instead of sending venue searches to DBLP.
- `queries`: List of plain-text venue labels. They are still URL-encoded with the keyword to preserve cache-key and Issue-link compatibility.
- `mails`: The first email address (`mails[0]`) is used as the `contact_email` for the Crossref API User-Agent (`mailto:...`), which is recommended for polite API access. Additional addresses are reserved for future mail-notification features.
- **Agent Note**: When adding a venue, append its query label to `dblp.queries` and its XML record-key prefix to `dblp.snapshot.query_key_prefixes`.
- **Backward compatibility**: Old single-string `keyword` field is still supported and is automatically wrapped into a one-element list.

### 7. Relevance Filtering
- `dblp.filters.exclude_title_keywords` contains global, case-insensitive title exclusions. Expression tokens match consecutive title-token prefixes, allowing stems such as `federat`.
- `dblp.filters.require_any_by_keyword` maps broad search keywords to positive systems/efficiency context expressions. At least one expression must be present in the title.
- Both snapshot and legacy API modes apply the same rules before caching or enrichment.
- After changing filter rules, run `python scripts/filter_cache.py --dry-run`, then `python scripts/filter_cache.py` and `python scripts/convert_cache_to_md.py` to update existing data.
- **Agent Note**: Prefer positive context rules for broad keywords over long lists of application-domain exclusions. Add tests for every new filtering behavior.

### 8. Awesome-AIInfra Curation Boundary
- `AIInfra-Papers.md` is the automated candidate list; [Awesome-AIInfra](https://github.com/lys122519/Awesome-AIInfra) is the reviewed knowledge base.
- `scripts/curation.py` includes main proceedings, Findings, and industry tracks while explicitly excluding workshops, demos, posters, tutorials, student tracks, companion volumes, and position papers.
- `scripts/export_candidates.py` exports structured review batches. Records remain `reviewed: false` unless a human has checked relevance, metadata, and category placement.
- Never push tracker candidates directly into Awesome-AIInfra without a reviewable pull request.

## Maintenance Notes

### Adding a New Venue
1. Find the DBLP venue code and XML record-key prefix (e.g., `venue:ICML:` and `conf/icml`).
2. Append the query string to `dblp.queries` and the matching prefix to `dblp.snapshot.query_key_prefixes`.
3. Update `scripts/convert_cache_to_md.py` if you want the new venue mapped to a specific category in `AIInfra-Papers.md`.
4. Update `README.md` (both EN and CN sections) to list the new venue.
5. Update this `AGENTS.md` if the change affects architecture or conventions.

### Backfilling Abstracts for Existing Papers
- A standalone script `scripts/fetch_abstracts.py` is provided to backfill `abstract` fields for papers already in `cached/dblp.yaml`.
- It queries five APIs in order until a non-empty abstract is found:
  1. **OpenReview** (priority, batch-only for OpenReview-source papers) — Inside `fetch_abstract_for_papers()` a *prefill stage* (`_prefill_openreview_abstracts`) scans every paper whose `ee` contains `openreview.net`, extracts the forum id (`forum?id=XXX` / `pdf?id=XXX`), and asks the OpenReview **v2 batch endpoint** `api2.openreview.net/notes?ids=A,B,C` (≤100 ids per call). Any id missed by v2 falls back to per-id queries against v2 then v1 (`api.openreview.net/notes?forum=XXX`). Both API content schemas are handled (`v1` plain string vs `v2` `{value: "..."}`). Inspired by the [PaperVault](https://github.com/youngfish42/PaperVault) project.
  2. **Crossref** — by DOI, with `contact_email` in the User-Agent header.
  3. **Semantic Scholar** — by DOI.
  4. **arXiv** — by title via `export.arxiv.org/api/query`, parsing Atom XML. arXiv enforces a minimum 3-second interval between requests.
  5. **OpenAlex** (final fallback) — by DOI via `api.openalex.org/works/doi:...`. OpenAlex returns `abstract_inverted_index`, which is reconstructed into plain text. A `mailto` parameter is appended when `contact_email` is available.
- All queries use rate limiting, timeout handling (10s + exponential backoff), and automatic newline cleaning.
- The cache is backed up to `cached/dblp.yaml.bak` before each overwrite; `*.bak` files are ignored by git (see `.gitignore`).
- Usage:
  ```bash
  # Process current-year papers (default)
  python scripts/fetch_abstracts.py
  # Process all years
  python scripts/fetch_abstracts.py --year all
  # Retry previously failed entries (empty abstracts)
  python scripts/fetch_abstracts.py --retry-failed
  ```
- **Automatic abstract fetching**: `src/main.py` already calls `fetch_abstract_for_papers()` for every batch of new papers before saving the cache, so newly discovered papers get their abstracts filled automatically during the daily GitHub Actions run.
- **Automatic related code extraction**: Immediately after a non-empty English `abstract` is obtained, `extract_github_links()` scans the text for `https://github.com/<user>/<repo>` patterns and stores the first match in `related_code`. This happens inside `fetch_abstract_for_papers()` (both in the OpenReview prefill stage and the per-paper fallback loop), so new papers get their code links without extra steps.
- **Automatic Chinese translation**: After a non-empty English `abstract` is obtained, `translate_abstracts_for_papers()` calls **Qwen-MT-plus** (via the Alibaba Cloud Bailian OpenAI-compatible API) to translate the abstract into Chinese, storing it as `abstract_cn`. Translation is skipped if the `DASHSCOPE_API_KEY` environment variable is missing, and individual translation failures do not block the pipeline.

### Backfilling DOIs for Existing Papers
- A standalone script `scripts/fetch_dois.py` is provided to backfill missing `doi` fields for papers already in `cached/dblp.yaml`.
- It queries APIs in the following priority order until a non-empty DOI is found:
  1. **DBLP API** (primary) — re-queries the paper by its `key` (e.g. `conf/dac/ChandrasekaranE22`) to check whether a DOI has been assigned since the initial fetch. This is the most authoritative source.
  2. **Crossref** (fallback) — searches by title via `api.crossref.org/works?query.title=...`.
  3. **Semantic Scholar** (final fallback) — searches by title via `api.semanticscholar.org/graph/v1/paper/search`.
- All queries use rate limiting, timeout handling (10s + exponential backoff), and title fuzzy-matching verification (`is_title_match`) to avoid assigning an incorrect DOI.
- The cache is backed up to `cached/dblp.yaml.bak` before each overwrite; `*.bak` files are ignored by git (see `.gitignore`).
- Usage:
  ```bash
  # Process current-year papers with missing DOI (default)
  python scripts/fetch_dois.py
  # Process all years
  python scripts/fetch_dois.py --year all
  # Re-fetch DOI for all papers (even those that already have one)
  python scripts/fetch_dois.py --retry-all
  ```
- A GitHub Actions workflow `.github/workflows/backfill-dois.yml` allows manual triggering from the repository UI.

### Backfilling Related Code for Existing Papers
- A standalone script `scripts/fetch_related_code.py` is provided to backfill missing `related_code` fields for papers already in `cached/dblp.yaml`.
- It scans the `abstract` text of each paper for GitHub repository URLs (`https://github.com/<user>/<repo>`), cleans trailing punctuation, and stores the first match in `related_code`.
- The cache is backed up to `cached/dblp.yaml.bak` before each overwrite; `*.bak` files are ignored by git (see `.gitignore`).
- Usage:
  ```bash
  # Process current-year papers (default)
  python scripts/fetch_related_code.py
  # Process all years
  python scripts/fetch_related_code.py --year all
  # Retry previously failed entries (empty related_code)
  python scripts/fetch_related_code.py --retry-failed
  ```
- **Automatic related code extraction**: `src/main.py` already calls `extract_github_links()` inside `fetch_abstract_for_papers()` for every batch of new papers, so newly discovered papers get their code links filled automatically during the daily GitHub Actions run.

### Switching to a Different Research Domain
The tracker remains domain-agnostic. To pivot away from the current AI Infrastructure focus:

1. **Change the keywords** in `config.yaml`:
   ```yaml
   dblp:
     keywords:
       - storage system   # example only
   ```
2. **Adjust the venue list** under `dblp.queries` to match the venues relevant to the new domain.
3. **Update `scripts/convert_cache_to_md.py`**:
   - `VENUE_MAP` — map DBLP raw venue names to your preferred display names.
   - `CATEGORY_MAP` — assign each display name to a category.
   - `CATEGORY_ORDER` and `VENUE_ORDER` — control the output ordering.
4. (Optional) Remove inactive keys from `cached/dblp.yaml` to reclaim space. A reset is not needed for correctness because deduplication and Markdown generation ignore topics not present in the current configuration.
5. (Optional) Update `README.md` and `TECHNICAL.md` to reflect the new domain.

No changes to `src/main.py` or the GitHub Actions workflow are required. Review `primary_only` carefully before enabling it.

### Changing Message Format
- Edit `src/utils.py` → `get_msg`.
- If you modify the Markdown structure, verify that the issue template renders correctly in GitHub.
- Keep the `aggregated` parameter behavior: `True` = heading only, `False` = heading + list.
- The default list item format is `- {title}. [[PUB]({ee})]`. When `related_code` is present, it appends ` [[CODE]({related_code})]` after `[PUB]`.

### Changing Issue Template
- Edit `.github/issue-template.md`.
- The template engine is Nunjucks (via `JasonEtco/create-an-issue@v2`). Available variables:
  - `{{ date }}`
  - `{{ env.MSG }}`
  - `{{ env.ISSUE_TITLE_TOPICS }}`
- If you introduce a new `env` variable, also update `.github/workflows/watch.yml` to pass it through.

### Changing Workflow Schedule
- Edit `.github/workflows/watch.yml` → `schedule.cron`.
- Default is twice per month at 01:15 UTC, on days 3 and 17 (`15 1 3,17 * *`).

### Cache Corruption / Manual Reset
- Simply delete `cached/dblp.yaml` (or remove specific topic keys).
- The next run will treat all papers as "new" and recreate the cache.

## Testing Locally

```bash
python scripts/sync_dblp_snapshot.py
cd src
python main.py run --env=dev
```

The initial compressed snapshot download is about 1 GiB. Later runs reuse the same monthly release from `.cache/dblp/`.

In `dev` mode the script will:
- Load the cache
- Stream the local snapshot for **all** keywords and venues
- Print logs to stdout
- **Not** write to `GITHUB_ENV`

You can inspect `aggregated_msg` and `msg` in the logs to preview the issue content.

Additional CLI flags:
- `--primary_only` — Optional compatibility mode: the first keyword scans all venues and the remaining keywords only scan venues where it found new papers. It is not used by the current automatic workflow.
- `--all_years` — Disables the year filter and skips abstract fetching / translation (used by the `Fetch All Years Papers` workflow).
- `--keyword_limit`, `--query_limit`, and `--max_results` — Bound local processing scope.
- `--dry_run` and `--skip_enrichment` — Keep smoke tests read-only and avoid external metadata calls.
- `--fail_on_request_error` — Legacy API-mode option that turns request failures into a non-zero exit.

## Common Pitfalls

1. **Snapshot Size**: The official gzip release is about 1 GiB. Keep it under `.cache/dblp/`, never commit it, stream the XML, and retain the release-keyed Actions cache. Do not add challenge-solving or verification-bypass code; `source: api` remains only a legacy compatibility path.
2. **YAML Encoding**: `cached/dblp.yaml` is written with `allow_unicode=True`. Editing it manually with an editor that strips Unicode may corrupt author names.
3. **Empty `ee` Field**: Some older DBLP entries lack an `ee`. The deduplication logic skips empty `ee` values, so those papers are always retained. This is intentional to avoid data loss.
4. **Topic String Parsing**: `get_topic_short_name` relies on `split(":")[-2]` followed by `split("/")[-1]`. If DBLP changes its topic URL format, this will break.

## Contact & References

- Upstream inspiration: [dblp-watcher](https://github.com/beiyuouo/dblp-watcher/)
- Official DBLP XML releases: https://drops.dagstuhl.de/entities/collection/10.4230/dblp.xml
