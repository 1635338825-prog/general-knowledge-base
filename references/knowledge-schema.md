# Knowledge Schema

The stable contract is now:

1. parser output
2. digest
3. rendered pages

The script does not heuristically understand the source, topic, or entity. Codex or another LLM does.

## Parser Outputs

Each source should first produce:

- `derived/<source-id>/content.json`
- `derived/<source-id>/content.md`

`content.json` is the main digestion input. `content.md` is supporting context.

## Semi-Automatic Digest Flow

### Source

1. `prepare-source` reads parsed outputs
2. the script writes `bundle.json` plus `prompt.md`
3. Codex reads the bundle and outputs pure JSON
4. `apply-digest` validates and persists that JSON

### Topic

1. `prepare-topic` collects source digests that mention the topic
2. Codex reads the bundle and outputs pure JSON
3. `apply-topic` validates and persists that JSON

If the topic page already exists and a newly digested source adds meaningful new evidence, methods, mechanisms, or result context, Codex should regenerate the topic digest rather than leaving the old topic page unchanged.

### Entity

1. `prepare-entity` collects source digests that mention the entity
2. Codex reads the bundle and outputs pure JSON
3. `apply-entity` validates and persists that JSON

If the entity page already exists and a newly digested source materially changes how that entity is framed, measured, interpreted, or connected to results, Codex should regenerate the entity digest in the same conversation.
If the entity is already clearly central to the research line and is supported by current source digests, Codex should create the entity page instead of leaving it only as a source-level tag.

This is intentionally not an API auto-call workflow.

## Source Digest

Write `derived/<source-id>/digest.json` with at least these fields:

```json
{
  "source_id": "",
  "title": "",
  "canonical_title": "",
  "knowledge_type": "paper|policy|method-note|data-note|general",
  "source_language": "zh|en",
  "background": [],
  "treatment": [],
  "details": [],
  "results_and_contribution": [],
  "topics": [],
  "entities": [],
  "structured_at": ""
}
```

Meaning of the four正文 sections:

- `background`: 研究问题、情境、动机、对象
- `treatment`: 怎么做，识别、方法、数据、变量、实验设计
- `details`: 为什么这么做，关键假设、机制、方法选择理由、重要限制与解释点
- `results_and_contribution`: 发现了什么、与既有研究相比贡献是什么、对当前知识主线有什么增量

Internal compatibility fields may also exist, for example:

- `methods`
- `results`
- `key_details`
- `identification`
- `mechanisms`
- `limitations`

They may remain for backward compatibility, but the rendered page contract centers on the new four-section schema.

## Topic Digest

Write `derived/topics/<topic>.json` with at least:

```json
{
  "topic": "",
  "title": "",
  "background": [],
  "treatment": [],
  "details": [],
  "results_and_contribution": [],
  "source_ids": [],
  "structured_at": ""
}
```

This is not a lightweight concept card. It should explain how the topic is handled across multiple sources and why it matters in the current knowledge line.

## Entity Digest

Write `derived/entities/<entity>.json` with at least:

```json
{
  "entity": "",
  "title": "",
  "background": [],
  "treatment": [],
  "details": [],
  "results_and_contribution": [],
  "source_ids": [],
  "structured_at": ""
}
```

`entity.background` is not a generic dictionary definition. It should explain the entity's problem background and usage background in the current research line.

## Human Pages

### `wiki/sources/*.md`

Visible headings:

- `背景`
- `处理`
- `细节`
- `结果与贡献`
- `相关主题`
- `相关实体`

### `wiki/topics/*.md`

Visible headings:

- `背景`
- `处理`
- `细节`
- `结果与贡献`
- `相关来源`

### `wiki/entities/*.md`

Visible headings:

- `背景`
- `处理`
- `细节`
- `结果与贡献`
- `相关来源`

## Linking Rules

- Source pages should link to related topic pages and entity pages only when those pages already exist.
- Topic pages and entity pages should link back to supporting source pages.
- `apply-topic` and `apply-entity` should refresh affected source pages so backlinks appear immediately.
- During live Codex digestion, when a new source touches existing topics/entities, those pages should be treated as upgradeable knowledge nodes and refreshed in the same run.

## Quality Rules

- Source-page text must be rewritten digestion, not raw OCR paste.
- Topic and entity pages must be synthesis over source digests, not string concatenation over raw OCR.
- `purpose` must guide the digestion.
- `content.json` has priority over `content.md` when the two differ.
- Do not keep directory pages, cover pages, school metadata, author metadata, DOI strings, headers, footers, keyword bars, or OCR junk.
- If a source lacks `digest.json`, it is parsed but not digested.
- Entity coverage should emphasize value, not mere count:
  - do generate entity pages for core outcomes, policy objects, methods, measurement frameworks, and repeated mechanism variables
  - do not generate large numbers of weak, isolated, glossary-like entities only because they were extracted once
