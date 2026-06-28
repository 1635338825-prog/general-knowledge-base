# Thesis Mode

Use thesis mode when the vault is meant to actively support paper writing rather than only archive sources.

## Goal

Turn the vault into two layers:

1. knowledge pages
2. writing work surfaces

The knowledge layer is still built from:

- source pages
- topic pages
- entity pages

The writing layer adds:

- `wiki/core/`
- `wiki/literature/`
- `wiki/identification/`
- `wiki/drafts/`

## Minimum Thesis Starter Pages

### `wiki/core/`

- `主线缺口评估.md`
- `论文主线与章节地图.md`
- `当前最强证据包.md`
- `下一批应补文献.md`

### `wiki/literature/`

- `桥接文献清单.md`
- `候选文献池.md`
- `文献作用分组.md`

### `wiki/identification/`

- `识别策略卡.md`
- `识别威胁卡.md`
- `稳健性计划卡.md`
- `异质性计划卡.md`

### `wiki/drafts/`

- `摘要草稿.md`
- `文献综述草稿.md`
- `研究设计草稿.md`
- `实证结果草稿.md`
- `机制分析草稿.md`

## Encoding Rule

All Markdown and JSON files must be read and written as `UTF-8`.

On Windows, do not assume `Get-Content` default decoding is correct. Use:

```powershell
Get-Content -Raw -Encoding UTF8 .\purpose.md
```

## Command

```powershell
python .\scripts\wiki_task.py init-thesis-workspace --vault D:\MyWiki
```
