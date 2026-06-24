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
- `--structure/--no-structure`
- `--split-pages` with default `50`
- `--digest-engine codex|llm` with default `codex`

Behavior:

- PDF files are split into page chunks before parsing when `--split-pages > 0`
- each chunk is still parsed by MinerU VLM
- with `--digest-engine codex`, the script leaves the source in `parsed_only` and generates a Codex bundle plus prompt
- with `--digest-engine llm`, the run uses the low-level automatic LLM digestion path

### `ingest-folder`

Same contract as `ingest-file`, but batch-oriented.

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
- does not rerun MinerU

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
- must not rerun MinerU in either mode

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

- PDF failures must report MinerU errors and must not fall back to another parser.
- Missing `LLM_WIKI_MODEL` is not a parse failure. It is a valid `parsed_only` state.
- A source with `content.json` but no `digest.json` is not digested.
- `prepare-*` failure should preserve existing parsed outputs and existing digests.
- `apply-*` failure should not delete existing parsed outputs or existing pages.
