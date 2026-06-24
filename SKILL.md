---
name: general-knowledge-base
description: "Build and maintain an Obsidian-style personal knowledge base with MinerU VLM parsing, Codex or LLM digestion, rebuild, audit, and qmd retrieval."
---

# General Knowledge Base

## Overview

Engine: `Codex`

Use this skill when the goal is to operate the user's personal knowledge vault rather than summarize one file in isolation.

The stable contract is:

1. MinerU VLM parses source files into `derived/<source-id>/content.json` and `content.md`
2. Codex or another LLM digests parsed content into `derived/<source-id>/digest.json`
3. Scripts render digests into source / topic / entity pages
4. qmd indexes the resulting pages for retrieval

Do not use heuristic scripts to understand the source. Script logic is only for orchestration, validation, rebuild, linking, and audit.

Prefer the bundled entrypoint:

```powershell
python .\scripts\wiki_task.py <command> ...
```

## Locked Rules

- PDF parsing must use MinerU VLM.
- Large PDFs split by page count only. Default is `--split-pages 50`.
- `content.json` is the primary digestion input. `content.md` is supporting material.
- The preferred workflow is Codex-driven digestion, not heuristic structuring.
- `parsed_only` is a valid state.
- `rebuild` must not rerun MinerU.
- Source, topic, and entity understanding come from Codex or another LLM, not rule-based extraction.
- `purpose` is a first-class digestion input. Read it before digesting.

## Preferred Workflow

### Source

1. `ingest-file` or `ingest-folder` parses with MinerU VLM
2. the script leaves the source in `parsed_only`
3. the script generates:
   - `logs/codex-digest-bundles/<source-id>.json`
   - `logs/codex-digest-bundles/<source-id>.prompt.md`
4. Codex reads the bundle and outputs pure JSON
5. `apply-digest` validates that JSON, writes `derived/<source-id>/digest.json`, generates the source page, and updates `.wiki-cache.json`

### Topic

1. `prepare-topic`
2. Codex reads the bundle and outputs pure JSON
3. `apply-topic` validates that JSON, writes `derived/topics/<topic>.json`, generates `wiki/topics/<topic>.md`, and refreshes source backlinks

### Entity

1. `prepare-entity`
2. Codex reads the bundle and outputs pure JSON
3. `apply-entity` validates that JSON, writes `derived/entities/<entity>.json`, generates `wiki/entities/<entity>.md`, and refreshes source backlinks

If a new source digest materially updates an already existing topic or entity in the same Codex session, treat that topic or entity as an upgrade target in the same run and apply it immediately.

Entity generation rule:

- entity extraction in source digests is not enough by itself
- if a source or a batch of sources repeatedly surfaces a high-value entity for the current knowledge line, Codex should generate the entity page instead of leaving it only inside source digests
- high-value entities usually include:
  - core outcome variables
  - key policy objects
  - central method objects
  - canonical measurement frameworks
  - mechanism variables repeatedly used across sources
- prefer a smaller set of meaningful entity pages over a large set of weak glossary-like entities, but do not collapse to only one entity page when multiple core entities are already well supported

## Commands

### 1. Initialize

```powershell
python .\scripts\wiki_task.py init-vault --vault D:\MyWiki --title "我的个人知识库" --purpose "用于沉淀学习、研究、写作和项目资料"
```

### 2. Ingest One File

```powershell
python .\scripts\wiki_task.py ingest-file --file "<file>" --vault D:\MyWiki --tag 资料
```

For large PDFs:

```powershell
python .\scripts\wiki_task.py ingest-file --file "<large.pdf>" --vault D:\MyWiki --split-pages 50 --mineru-timeout 1200
```

If you explicitly want the old automatic LLM path:

```powershell
python .\scripts\wiki_task.py ingest-file --file "<file>" --vault D:\MyWiki --digest-engine llm
```

### 3. Ingest A Folder

```powershell
python .\scripts\wiki_task.py ingest-folder --folder "<folder>" --vault D:\MyWiki --pattern "*.pdf" --tag 资料
```

### 4. Prepare A Parsed Source For Codex

```powershell
python .\scripts\wiki_task.py prepare-source --vault D:\MyWiki --source-id <source-id>
```

### 5. Apply A Codex Source Digest

```powershell
python .\scripts\wiki_task.py apply-digest --vault D:\MyWiki --source-id <source-id> --digest-file "<digest.json>"
```

### 6. Audit Parsed Sources That Still Need Digestion

```powershell
python .\scripts\wiki_task.py audit-readiness --vault D:\MyWiki
```

### 7. Prepare A Topic For Codex

```powershell
python .\scripts\wiki_task.py prepare-topic --vault D:\MyWiki --topic "个人知识管理"
```

### 8. Apply A Codex Topic Digest

```powershell
python .\scripts\wiki_task.py apply-topic --vault D:\MyWiki --topic "个人知识管理" --digest-file "<topic-digest.json>"
```

### 9. Prepare An Entity For Codex

```powershell
python .\scripts\wiki_task.py prepare-entity --vault D:\MyWiki --entity "Obsidian vault"
```

### 10. Apply A Codex Entity Digest

```powershell
python .\scripts\wiki_task.py apply-entity --vault D:\MyWiki --entity "Obsidian vault" --digest-file "<entity-digest.json>"
```

Use `structure-source` as a compatibility alias for Codex bundle prep:

```powershell
python .\scripts\wiki_task.py structure-source --vault D:\MyWiki --source-id <source-id>
```

Use `structure-source` with the old automatic LLM path:

```powershell
python .\scripts\wiki_task.py structure-source --vault D:\MyWiki --source-id <source-id> --digest-engine llm
```

### 11. Rebuild

```powershell
python .\scripts\wiki_task.py rebuild --vault D:\MyWiki
```

Rebuild regenerates pages from existing digest files. It does not reparse files or auto-create new knowledge pages.

### 12. Query And Audit

```powershell
python .\scripts\wiki_task.py query --vault D:\MyWiki --question "<question>" --limit 5
```

```powershell
python .\scripts\wiki_task.py audit-vault --vault D:\MyWiki
```

## References

Read these files before changing the skill:

- `references/io-contract.md`
- `references/knowledge-schema.md`
- `references/retrieval-guidelines.md`
- `references/purpose-taxonomy.md`
- `references/command-cookbook.md`

