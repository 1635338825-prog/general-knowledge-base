# General Knowledge Base

`general-knowledge-base` 是一个通用个人知识库 skill，用于把论文、PDF、Word、PPT、Markdown、项目文档和网页转存资料沉淀为可检索、可复用的知识资产。

引擎：`Codex`

它基于 Obsidian 风格的 vault 组织资料，使用 MinerU VLM 解析源文件，使用 Codex 或其他 LLM 生成 `digest.json`，再把 digest 渲染为来源页、主题页和实体页，并通过 qmd 建立本地检索索引。

## 目录结构

```text
general-knowledge-base/
  README.md
  SKILL.md
  agents/
    openai.yaml
  references/
    command-cookbook.md
    io-contract.md
    knowledge-schema.md
    purpose-taxonomy.md
    retrieval-guidelines.md
  scripts/
    wiki_task.py
```

## 核心能力

- 多源资料接入：支持 `Markdown`、`TXT`、`PDF`、`PPT/PPTX`、`DOC/DOCX`
- MinerU VLM 解析：统一生成 `content.json` 和 `content.md`
- LLM 消化：用 Codex 或其他 LLM 生成结构化 `digest.json`
- 页面渲染：生成来源页、主题页和实体页
- qmd 检索：支持自然语言查询和证据回查
- 质量审计：识别 `parsed_only` 来源、缺失 digest、空壳页面和低价值实体

## 工作流

### 1. 初始化 vault

```powershell
python .\scripts\wiki_task.py init-vault --vault D:\MyWiki --title "我的个人知识库" --purpose "用于沉淀学习、研究、写作和项目资料"
```

### 2. 接入单个资料

```powershell
python .\scripts\wiki_task.py ingest-file --file "C:\path\document.pdf" --vault D:\MyWiki --tag 资料
```

默认流程：

- 使用 MinerU VLM 解析资料
- PDF 默认按 `50` 页拆分
- 生成 `derived/<source-id>/content.json`
- 生成 `logs/codex-digest-bundles/<source-id>.json`
- 生成 `logs/codex-digest-bundles/<source-id>.prompt.md`

### 3. 让 Codex 生成来源 digest

```powershell
python .\scripts\wiki_task.py prepare-source --vault D:\MyWiki --source-id <source-id>
python .\scripts\wiki_task.py apply-digest --vault D:\MyWiki --source-id <source-id> --digest-file "C:\path\digest.json"
```

### 4. 升级主题和实体

```powershell
python .\scripts\wiki_task.py prepare-topic --vault D:\MyWiki --topic "个人知识管理"
python .\scripts\wiki_task.py apply-topic --vault D:\MyWiki --topic "个人知识管理" --digest-file "C:\path\topic-digest.json"
python .\scripts\wiki_task.py prepare-entity --vault D:\MyWiki --entity "Obsidian vault"
python .\scripts\wiki_task.py apply-entity --vault D:\MyWiki --entity "Obsidian vault" --digest-file "C:\path\entity-digest.json"
```

### 5. 重建、查询与审计

```powershell
python .\scripts\wiki_task.py rebuild --vault D:\MyWiki
python .\scripts\wiki_task.py query --vault D:\MyWiki --question "这个知识库里关于某个主题有哪些内容？" --limit 5
python .\scripts\wiki_task.py audit-readiness --vault D:\MyWiki
python .\scripts\wiki_task.py audit-vault --vault D:\MyWiki
```

## 规则

- PDF 解析必须使用 MinerU VLM
- `content.json` 是主要消化输入
- `parsed_only` 是合法中间状态
- `rebuild` 不能重新跑 MinerU
- 高价值实体应升级成独立实体页，而不只是停留在来源 digest 中

## 适用场景

- 个人学习资料沉淀
- 文献阅读与研究写作
- 方法论与概念整理
- 项目知识管理
- 长期个人知识库维护
