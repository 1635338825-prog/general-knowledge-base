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
- OCR 解析后端：默认使用 MinerU VLM，可选接入 Unlimited-OCR，统一生成 `content.json` 和 `content.md`
- 文献发现链路：支持通过 Sciverse API 搜索论文、导入候选结果、补 DOI/PDF 访问链接，并把可下载 PDF 回灌到知识库流程
- LLM 消化：用 Codex 或其他 LLM 生成结构化 `digest.json`
- 页面渲染：生成来源页、主题页和实体页
- qmd 检索：支持自然语言查询和证据回查
- 质量审计：识别 `parsed_only` 来源、缺失 digest、空壳页面和低价值实体

## 外部支持与 API

### MinerU 支持

- 角色定位：负责文档解析，把 PDF、PPT、DOCX 等资料转成结构化的 `content.json` 和 `content.md`
- 在本项目中的位置：默认解析后端，接在 `ingest-file` 和 `ingest-folder` 入口之后
- 环境变量：
  - `MINERU_TOKEN`：使用官方云端解析时的 token
  - `MINERU_API_URL`：如果你接的是自部署接口，可以显式指定服务地址
  - `MINERU_API_KEY`：自部署接口或网关鉴权时使用
- 当前项目里的调用方式：
  - 默认通过 `obsidian_llm_wiki` 底层链路调用 MinerU
  - 本 skill 侧重点是把解析结果稳定收敛为统一知识库输入
- 官方入口：
  - 官网：[MinerU](https://mineru.net/)
  - API 文档：[MinerU API Docs](https://mineru.net/apiManage/docs)
- 本项目实际使用的官方接口族：
  - 精准解析 API：`/api/v4/extract/task`
  - 批量文件 URL 解析：`/api/v4/file-urls/batch`
  - Agent 轻量解析接口：`/api/v1/agent/parse/url`、`/api/v1/agent/parse/file`

### Sciverse 支持

- 角色定位：负责文献发现，不直接做 OCR，而是先做论文检索、候选导入、DOI 落地页解析和 PDF 下载前置
- 在本项目中的位置：`sciverse-search -> sciverse-import -> sciverse-fetch -> sciverse-download`
- 环境变量：
  - `SCIVERSE_API_TOKEN`：调用 Sciverse API 的访问凭证
- 当前项目里的调用方式：
  - `sciverse-search`：调用元数据搜索接口获取论文结果
  - `sciverse-import`：把候选结果写入知识库缓存，状态为 `discovered_only`
  - `sciverse-fetch`：补 DOI 落地页、跳转链接和候选 PDF 链接
  - `sciverse-download`：下载真实 PDF，并可继续回灌到 MinerU / Unlimited-OCR 解析流程
- 官方入口：
  - 官网：[Sciverse](https://sciverse.space/)
  - 文档：[Sciverse Docs](https://sciverse.space/docs)
- 本项目当前使用的核心接口：
  - 元数据检索：`POST https://api.sciverse.space/meta-search`
- Sciverse 文档里还提供的相关能力：
  - `POST /agentic-search`
  - `GET /content`
  - `GET /resource`
  - `GET /meta-catalog`

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

- 默认使用 MinerU VLM 解析资料
- PDF 默认按 `50` 页拆分
- 生成 `derived/<source-id>/content.json`
- 生成 `logs/codex-digest-bundles/<source-id>.json`
- 生成 `logs/codex-digest-bundles/<source-id>.prompt.md`

如需改用 Unlimited-OCR：

```powershell
python .\scripts\wiki_task.py ingest-file --file "C:\path\document.pdf" --vault D:\MyWiki --ocr-engine unlimited-ocr --unlimited-ocr-project "C:\path\Unlimited-OCR"
```

Unlimited-OCR 目前在这个 skill 里承担的是解析层，输出会被适配成与 MinerU 相同的 `content.md` 和 `content.json` 结构，后续 digest、主题页、实体页和 qmd 检索流程保持不变。

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

### 6. 用 Sciverse 搜索并导入论文

```powershell
$env:SCIVERSE_API_TOKEN = "<token>"
python .\scripts\wiki_task.py sciverse-search --vault D:\MyWiki --query "graphene battery cycle stability" --page-size 5
python .\scripts\wiki_task.py sciverse-import --vault D:\MyWiki --search-results "D:\MyWiki\logs\sciverse-search\<results>.results.json" --indexes 1,2 --purpose-role direct-evidence
python .\scripts\wiki_task.py sciverse-fetch --vault D:\MyWiki --source-id <source-id>
python .\scripts\wiki_task.py sciverse-download --vault D:\MyWiki --source-id <source-id>
```

Sciverse 链路会先把搜索结果注册成 `discovered_only` 候选来源，再补 DOI 落地页和候选 PDF 链接；只有在 `sciverse-download` 成功拿到真实 PDF 后，才会继续进入 MinerU 或 Unlimited-OCR 的解析流程。

## 后端选择建议

- `mineru`：默认后端，适合现有工作流，兼容性更稳
- `unlimited-ocr`：适合做 PDF/扫描件解析对比，当前建议作为可选后端逐步验证

如果使用 `unlimited-ocr`，建议优先在这几类 PDF 上做对比：

- 小 PDF
- 扫描 PDF
- 长 PDF
- 中英文混排 PDF
- 含表格或公式的 PDF

## 规则

- PDF 解析默认使用 MinerU VLM，也可以在明确指定时使用 Unlimited-OCR
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
