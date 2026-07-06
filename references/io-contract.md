# Script I/O Contract

Use `scripts/wiki_task.py` as the stable entrypoint.

## Common Report

Every command writes:

- `<vault>/logs/skill-runs/<run-id>.json`
- `<vault>/logs/skill-runs/<run-id>.md`

Common JSON shape:

```json
{
  "run_id": "",
  "command": "",
  "status": "success|partial|failed",
  "started_at": "",
  "finished_at": "",
  "inputs": {},
  "environment": {},
  "results": {},
  "generated_files": [],
  "updated_files": [],
  "skipped": [],
  "errors": [],
  "next_paths": []
}
```

## Commands

### `init-vault`

Required:

- `--vault`
- `--title`
- `--purpose`

Optional:

- `--language`
- `--project`

### `ingest-file`

Required:

- `--file`
- `--vault`

Optional:

- `--project`
- `--tag`
- `--title`
- `--mineru-timeout`
- `--ocr-engine mineru|unlimited-ocr` with default `mineru`
- `--unlimited-ocr-project` when `--ocr-engine unlimited-ocr`
- `--unlimited-ocr-concurrency`
- `--structure/--no-structure`
- `--split-pages` with default `50`
- `--digest-engine codex|llm` with default `codex`

Behavior:

- PDF files are split into page chunks before parsing when `--split-pages > 0`
- each chunk is parsed by the selected OCR backend
- `mineru` remains the default parser
- `unlimited-ocr` is an optional parser and currently supports only the `codex` digest workflow
- `unlimited-ocr` output must be normalized into the same `derived/<source-id>/content.json` and `content.md` files used by MinerU
- with `--digest-engine codex`, the script leaves the source in `parsed_only` and generates a Codex bundle plus prompt
- with `--digest-engine llm`, the run uses the low-level automatic LLM digestion path

### `ingest-folder`

Same contract as `ingest-file`, but batch-oriented.

### `web-ingest`

Required:

- `--url`
- `--vault`

Optional:

- `--tag`
- `--title`
- `--force/--no-force`
- `--digest-engine codex|llm` with default `codex`

Behavior:

- uses Firecrawl to scrape a live web page into Markdown
- writes normalized `derived/<source-id>/content.json` and `content.md`
- stores the original URL under `raw/<source-id>/source-url.txt`
- updates `.wiki-cache.json`
- with `--digest-engine codex`, generates a Codex bundle plus prompt by default
- with `--force`, refreshes an already known web source

### `firecrawl-ingest`

Same contract and behavior as `web-ingest`. This is an explicit alias for the Firecrawl-backed web ingestion path.

### `prepare-source`

Required:

- `--vault`
- `--source-id`

Optional:

- `--output`
- `--prompt-output`

Behavior:

- reads existing `derived/<source-id>/content.json` and `content.md`
- writes `logs/codex-digest-bundles/<source-id>.json` unless overridden
- writes `logs/codex-digest-bundles/<source-id>.prompt.md` unless overridden
- does not rerun parsing

### `apply-digest`

Required:

- `--vault`
- `--source-id`
- `--digest-file`

Behavior:

- validates the source digest JSON
- writes `derived/<source-id>/digest.json`
- generates the source page
- updates `.wiki-cache.json`
- in a live Codex conversation, this source digest should also be treated as new evidence for already existing topic/entity pages
- if the new source materially enriches an existing topic/entity, Codex should regenerate that topic/entity digest in the same conversation and then apply it
- if the new source introduces a high-value entity that already has enough support in current digests, Codex should prefer generating an entity page rather than leaving that entity only in the source-level `entities` list

Required source fields:

- `source_id`
- `title` or `canonical_title`
- `knowledge_type`
- `source_language`
- `background`
- `treatment`
- `details`
- `results_and_contribution`
- `topics`
- `entities`

Compatibility:

- old source digests using fields such as `methods`, `results`, `key_details`, `identification`, `mechanisms`, or `limitations` are accepted and mapped into the new four-section contract

### `prepare-topic`

Required:

- `--vault`
- `--topic`

Optional:

- `--output`
- `--prompt-output`

Behavior:

- collects all digested sources that mention the topic
- writes `logs/codex-index-bundles/topics/<topic>.json`
- writes `logs/codex-index-bundles/topics/<topic>.prompt.md`
- when used inside a live Codex digestion session, this bundle is both a creation input for a new topic and an upgrade input for an existing topic

### `apply-topic`

Required:

- `--vault`
- `--topic`
- `--digest-file`

Behavior:

- validates the topic digest JSON
- writes `derived/topics/<topic>.json`
- generates `wiki/topics/<topic>.md`
- refreshes source backlinks
- updates `.wiki-cache.json`

Required topic fields:

- `topic`
- `title`
- `background`
- `treatment`
- `details`
- `results_and_contribution`
- `source_ids`

Compatibility:

- old topic digests using `definition`, `treatment_and_method`, or `findings_and_contribution` are accepted and mapped

### `prepare-entity`

Required:

- `--vault`
- `--entity`

Optional:

- `--output`
- `--prompt-output`

Behavior:

- collects all digested sources that mention the entity
- writes `logs/codex-index-bundles/entities/<entity>.json`
- writes `logs/codex-index-bundles/entities/<entity>.prompt.md`
- when used inside a live Codex digestion session, this bundle is both a creation input for a new entity and an upgrade input for an existing entity

Priority rule:

- entity pages should be created first for high-value entities in the current research line
- examples include core outcomes, policy objects, central methods, canonical measurement frameworks, and repeated mechanism variables
- the contract prefers a compact set of meaningful entity pages over low-value glossary expansion, but it should not leave obviously central entities unmaterialized

### `apply-entity`

Required:

- `--vault`
- `--entity`
- `--digest-file`

Behavior:

- validates the entity digest JSON
- writes `derived/entities/<entity>.json`
- generates `wiki/entities/<entity>.md`
- refreshes source backlinks
- updates `.wiki-cache.json`

Required entity fields:

- `entity`
- `title`
- `background`
- `treatment`
- `details`
- `results_and_contribution`
- `source_ids`

Compatibility:

- old entity digests using `definition`, `measurement_and_identification`, or `role_in_results` are accepted and mapped

### `audit-readiness`

Required:

- `--vault`

Output:

- parsed-but-not-digested source count
- per-source paths for pending sources
- suggested bundle path for each pending source

### `structure-source`

Required:

- `--vault`
- one of `--source-id` or `--source-page`

Optional:

- `--project`
- `--digest-engine codex|llm` with default `codex`

Behavior:

- with `codex`, this is a compatibility alias for preparing a source bundle and prompt
- with `llm`, this runs the old automatic digestion path
- must not rerun parsing in either mode

### `rebuild`

Required:

- `--vault`

Optional:

- `--project`
- `--refresh-qmd/--no-refresh-qmd`

Behavior:

- rebuilds source pages from existing source digests
- rebuilds tracked topic/entity pages from existing topic/entity digests
- prunes legacy heuristic topic/entity pages that are not tracked
- refreshes overview
- does not reparse PDFs
- does not auto-create new topic/entity knowledge
- does not replace the live-conversation Codex upgrade rule; it only rewrites pages from already applied digests

### `query`

Required:

- `--vault`
- `--question`

Optional:

- `--project`
- `--limit`

### `sciverse-search`

Required:

- `--vault`
- `--query`

Optional:

- `--page`
- `--page-size`
- `--field` repeatable
- `--filter-json`
- `--output`
- `--save-raw/--no-save-raw`

Behavior:

- reads `SCIVERSE_API_TOKEN` from the environment
- calls `https://api.sciverse.space/meta-search`
- writes normalized results under `logs/sciverse-search/*.results.json`
- optionally writes the raw API response under `logs/sciverse-search/*.raw.json`
- does not create source pages or parsed content

### `sciverse-import`

Required:

- `--vault`
- `--search-results`

Optional:

- `--indexes`
- `--all`
- `--tag` repeatable
- `--purpose-role`

Behavior:

- reads a prior `sciverse-search` `results.json`
- imports selected hits into `.wiki-cache.json` as `discovered_only` sources
- writes `derived/<source-id>/sciverse.json` for each imported source
- does not download files
- does not run MinerU or Unlimited-OCR
- does not create `content.json`, `content.md`, `digest.json`, or source pages

### `sciverse-fetch`

Required:

- `--vault`
- one of `--source-id` or `--all`

Behavior:

- reads Sciverse-imported `discovered_only` sources from cache
- resolves the DOI landing page when a DOI exists
- updates `derived/<source-id>/sciverse.json` with access metadata
- updates cache fields such as `doi_url`, `resolved_url`, and optionally `pdf_candidate_url`
- does not download the PDF
- does not create parsed content or digests

### `sciverse-download`

Required:

- `--vault`
- one of `--source-id` or `--all`

Optional:

- `--ingest/--no-ingest`
- `--project`
- `--mineru-timeout`
- `--split-pages`
- `--ocr-engine mineru|unlimited-ocr`
- `--unlimited-ocr-project`
- `--unlimited-ocr-concurrency`

Behavior:

- reads Sciverse-imported sources from cache
- tries to download a real PDF using `pdf_candidate_url` or DOI-derived PDF heuristics
- saves the PDF under `raw/sciverse/`
- with default `--ingest`, immediately runs `ingest-file` on the downloaded PDF
- if ingest succeeds, merges the old `discovered_only` candidate metadata into the ingested source record
- if the remote URL is HTML or otherwise not a real PDF, the source is skipped instead of sending a bad file to ingest

### `audit-vault`

Required:

- `--vault`

## Bundle Contracts

### Source Bundle

`prepare-source` writes a bundle JSON with at least:

```json
{
  "source_id": "",
  "generated_at": "",
  "vault_path": "",
  "purpose": "",
  "source_record": {},
  "derived": {
    "content_json_path": "",
    "content_markdown_path": "",
    "content_json": {},
    "content_markdown": ""
  },
  "digest_contract": {
    "required_string_fields": [],
    "required_list_fields": ["background", "treatment", "details", "results_and_contribution", "topics", "entities"],
    "output_path": ""
  },
  "page_contract": {
    "visible_sections": ["背景", "处理", "细节", "结果与贡献"],
    "link_sections": ["相关主题", "相关实体"]
  }
}
```

### Topic Bundle

`prepare-topic` writes:

```json
{
  "kind": "topic",
  "topic": "",
  "generated_at": "",
  "vault_path": "",
  "purpose": "",
  "supporting_sources": [],
  "digest_contract": {
    "required_string_fields": ["topic", "title"],
    "required_list_fields": ["background", "treatment", "details", "results_and_contribution", "source_ids"],
    "output_path": ""
  }
}
```

### Entity Bundle

`prepare-entity` writes:

```json
{
  "kind": "entity",
  "entity": "",
  "generated_at": "",
  "vault_path": "",
  "purpose": "",
  "supporting_sources": [],
  "digest_contract": {
    "required_string_fields": ["entity", "title"],
    "required_list_fields": ["background", "treatment", "details", "results_and_contribution", "source_ids"],
    "output_path": ""
  }
}
```

## Failure Rules

- Parse failures must report the selected backend error and must not silently fall back to another parser.
- Missing `LLM_WIKI_MODEL` is not a parse failure. It is a valid `parsed_only` state.
- A source with `content.json` but no `digest.json` is not digested.
- `prepare-*` failure should preserve existing parsed outputs and existing digests.
- `apply-*` failure should not delete existing parsed outputs or existing pages.
