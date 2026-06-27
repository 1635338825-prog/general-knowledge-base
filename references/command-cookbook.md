# Command Cookbook

Prefer `scripts/wiki_task.py` for normal work. Use the low-level CLI only when debugging the tool itself.

## Script Commands

Initialize a vault:

```powershell
python .\scripts\wiki_task.py init-vault --vault D:\MyWiki --title "我的个人知识库" --purpose "用于沉淀学习、研究、写作和项目资料"
```

Ingest one file and prepare a Codex source bundle:

```powershell
python .\scripts\wiki_task.py ingest-file --file "C:\path\document.pdf" --vault D:\MyWiki --tag 资料
```

Ingest one file with Unlimited-OCR as the parsing backend:

```powershell
python .\scripts\wiki_task.py ingest-file --file "C:\path\document.pdf" --vault D:\MyWiki --tag 资料 --ocr-engine unlimited-ocr --unlimited-ocr-project "C:\path\Unlimited-OCR"
```

Ingest a folder of PDFs:

```powershell
python .\scripts\wiki_task.py ingest-folder --folder "C:\path\docs" --vault D:\MyWiki --pattern "*.pdf" --tag 资料
```

Ingest a folder with Unlimited-OCR:

```powershell
python .\scripts\wiki_task.py ingest-folder --folder "C:\path\docs" --vault D:\MyWiki --pattern "*.pdf" --tag 资料 --ocr-engine unlimited-ocr --unlimited-ocr-project "C:\path\Unlimited-OCR"
```

Prepare a parsed source for Codex digestion:

```powershell
python .\scripts\wiki_task.py prepare-source --vault D:\MyWiki --source-id <source-id>
```

Apply a Codex-generated source digest:

```powershell
python .\scripts\wiki_task.py apply-digest --vault D:\MyWiki --source-id <source-id> --digest-file C:\path\digest.json
```

Audit parsed sources that still need digestion:

```powershell
python .\scripts\wiki_task.py audit-readiness --vault D:\MyWiki
```

Prepare a topic bundle:

```powershell
python .\scripts\wiki_task.py prepare-topic --vault D:\MyWiki --topic "个人知识管理"
```

Apply a topic digest:

```powershell
python .\scripts\wiki_task.py apply-topic --vault D:\MyWiki --topic "个人知识管理" --digest-file C:\path\topic-digest.json
```

Prepare an entity bundle:

```powershell
python .\scripts\wiki_task.py prepare-entity --vault D:\MyWiki --entity "Obsidian vault"
```

Apply an entity digest:

```powershell
python .\scripts\wiki_task.py apply-entity --vault D:\MyWiki --entity "Obsidian vault" --digest-file C:\path\entity-digest.json
```

Use `structure-source` as a compatibility alias for Codex bundle prep:

```powershell
python .\scripts\wiki_task.py structure-source --vault D:\MyWiki --source-id <source-id>
```

Use `structure-source` with the old automatic LLM path:

```powershell
python .\scripts\wiki_task.py structure-source --vault D:\MyWiki --source-id <source-id> --digest-engine llm
```

Rebuild from existing digests:

```powershell
python .\scripts\wiki_task.py rebuild --vault D:\MyWiki
```

Query:

```powershell
python .\scripts\wiki_task.py query --vault D:\MyWiki --question "这个知识库里关于某个主题有哪些内容？" --limit 5
```

Audit:

```powershell
python .\scripts\wiki_task.py audit-vault --vault D:\MyWiki
```

Search Sciverse:

```powershell
$env:SCIVERSE_API_TOKEN = "<token>"
python .\scripts\wiki_task.py sciverse-search --vault D:\MyWiki --query "graphene battery cycle stability" --page-size 5
```

Import selected Sciverse results as candidate sources:

```powershell
python .\scripts\wiki_task.py sciverse-import --vault D:\MyWiki --search-results "D:\MyWiki\logs\sciverse-search\<results>.results.json" --indexes 1,2 --purpose-role direct-evidence
```

Resolve DOI landing pages and store access URLs:

```powershell
python .\scripts\wiki_task.py sciverse-fetch --vault D:\MyWiki --source-id <source-id>
```

Download a candidate PDF and ingest it immediately:

```powershell
python .\scripts\wiki_task.py sciverse-download --vault D:\MyWiki --source-id <source-id>
```

## Codex Digest Loops

### Source

1. `ingest-file` or `prepare-source`
2. open `logs/codex-digest-bundles/<source-id>.prompt.md`
3. let Codex read the adjacent bundle and output pure JSON
4. save that JSON
5. `apply-digest`

When `--ocr-engine unlimited-ocr` is used, the OCR backend only replaces the parsing stage. The downstream bundle, digest, topic/entity, and retrieval workflow stays unchanged because the script normalizes output into the same `content.json` and `content.md` contract.

The output should be a real digestion of the whole source, not a short summary. The four required body sections are:

- `background`
- `treatment`
- `details`
- `results_and_contribution`

### Topic

1. `prepare-topic`
2. open `logs/codex-index-bundles/topics/<topic>.prompt.md`
3. let Codex read the adjacent bundle and output pure JSON
4. save that JSON
5. `apply-topic`

Topic digestion should explain how the topic runs through multiple sources, not just define the term.

### Entity

1. `prepare-entity`
2. open `logs/codex-index-bundles/entities/<entity>.prompt.md`
3. let Codex read the adjacent bundle and output pure JSON
4. save that JSON
5. `apply-entity`

Entity pages should be reserved for high-value recurring concepts, not weak glossary debris.


