from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_SECTIONS = [
    ("背景", "background"),
    ("处理", "treatment"),
    ("细节", "details"),
    ("结果与贡献", "results_and_contribution"),
]
TOPIC_SECTIONS = SOURCE_SECTIONS
ENTITY_SECTIONS = SOURCE_SECTIONS
SOURCE_SECTION_NAMES = {heading for heading, _ in SOURCE_SECTIONS}
TOPIC_SECTION_NAMES = {heading for heading, _ in TOPIC_SECTIONS}
ENTITY_SECTION_NAMES = {heading for heading, _ in ENTITY_SECTIONS}
SOURCE_REQUIRED_LIST_FIELDS = ["background", "treatment", "details", "results_and_contribution", "topics", "entities"]
TOPIC_REQUIRED_LIST_FIELDS = ["background", "treatment", "details", "results_and_contribution", "source_ids"]
ENTITY_REQUIRED_LIST_FIELDS = ["background", "treatment", "details", "results_and_contribution", "source_ids"]
SOURCE_INTERNAL_OPTIONAL_LIST_FIELDS = [
    "research_questions",
    "data_and_sample",
    "identification",
    "variable_measurement",
    "mechanisms",
    "heterogeneity",
    "robustness",
    "limitations",
    "methods",
    "results",
    "key_details",
]
TOPIC_INTERNAL_OPTIONAL_LIST_FIELDS = ["definition", "treatment_and_method", "findings_and_contribution"]
ENTITY_INTERNAL_OPTIONAL_LIST_FIELDS = ["definition", "measurement_and_identification", "role_in_results"]


def now_id(command: str) -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{command}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


THESIS_STARTER_PAGES = {
    "core/主线缺口评估.md": """# 主线缺口评估

## 当前主线

- 研究问题：
- 核心结果：
- 识别主轴：
- 机制主轴：

## 已经够用的部分

- 暂无内容

## 还要补强的部分

- 暂无内容
""",
    "core/论文主线与章节地图.md": """# 论文主线与章节地图

## 一句话主线

- 暂无内容

## 章节地图

- 第一章：
- 第二章：
- 第三章：
- 第四章：
- 第五章：
- 第六章：
""",
    "core/当前最强证据包.md": """# 当前最强证据包

## Direct Evidence

- 暂无内容

## Method Support

- 暂无内容

## Mechanism Evidence

- 暂无内容
""",
    "core/下一批应补文献.md": """# 下一批应补文献

## 第一优先级

- 暂无内容

## 第二优先级

- 暂无内容
""",
    "literature/桥接文献清单.md": """# 桥接文献清单

## 政策到结果

- 暂无内容

## 机制到结果

- 暂无内容
""",
    "literature/候选文献池.md": """# 候选文献池

## 候选来源

- 暂无内容
""",
    "literature/文献作用分组.md": """# 文献作用分组

## Direct Evidence

- 暂无内容

## Mechanism Evidence

- 暂无内容

## Method Support

- 暂无内容

## Bridge Literature

- 暂无内容

## Writing Support

- 暂无内容
""",
    "identification/识别策略卡.md": """# 识别策略卡

## 主识别

- 暂无内容

## 配套检验

- 暂无内容
""",
    "identification/识别威胁卡.md": """# 识别威胁卡

## 主要威胁

- 暂无内容

## 对应回应

- 暂无内容
""",
    "identification/稳健性计划卡.md": """# 稳健性计划卡

## 已规划检验

- 暂无内容
""",
    "identification/异质性计划卡.md": """# 异质性计划卡

## 异质性方向

- 暂无内容
""",
    "drafts/摘要草稿.md": """# 摘要草稿

- 暂无内容
""",
    "drafts/文献综述草稿.md": """# 文献综述草稿

- 暂无内容
""",
    "drafts/研究设计草稿.md": """# 研究设计草稿

- 暂无内容
""",
    "drafts/实证结果草稿.md": """# 实证结果草稿

- 暂无内容
""",
    "drafts/机制分析草稿.md": """# 机制分析草稿

- 暂无内容
""",
}


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(read_text(path))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def json_safe(value: Any) -> Any:
    if callable(value):
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items() if not callable(item)}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value if not callable(item)]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = clean_text(item)
        if not text:
            continue
        lowered = text.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    if not result:
        raise ValueError(f"{field_name} must contain at least one non-empty item")
    return result


def as_bullets(values: Any) -> list[str]:
    items = values if isinstance(values, list) else [values]
    bullets = [f"- {clean_text(item)}" for item in items if clean_text(item)]
    return bullets or ["- 暂无内容"]


def merge_unique_lists(*values: Any) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        items = value if isinstance(value, list) else [value]
        for item in items:
            text = clean_text(item)
            if not text:
                continue
            lowered = text.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            merged.append(text)
    return merged


def first_non_empty_list(*values: Any) -> list[str]:
    for value in values:
        merged = merge_unique_lists(value)
        if merged:
            return merged
    return []


def load_cache(vault: Path) -> dict[str, Any]:
    cache = load_json(vault / ".wiki-cache.json", {"sources": {}, "topic_pages": {}, "entity_pages": {}})
    if not isinstance(cache, dict):
        cache = {}
    if not isinstance(cache.get("sources"), dict):
        cache["sources"] = {}
    if not isinstance(cache.get("topic_pages"), dict):
        cache["topic_pages"] = {}
    if not isinstance(cache.get("entity_pages"), dict):
        cache["entity_pages"] = {}
    return cache


def save_cache(vault: Path, cache: dict[str, Any]) -> None:
    dump_json(vault / ".wiki-cache.json", cache)


def load_config(vault: Path) -> dict[str, Any]:
    config = load_json(vault / ".wiki-config.json", {})
    return config if isinstance(config, dict) else {}


def vault_purpose(vault: Path) -> str:
    config = load_config(vault)
    return clean_text(config.get("purpose")) or "围绕当前论文主线持续消化资料并形成可检索知识库"


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def split_pdf(path: Path, output_dir: Path, pages_per_part: int) -> list[Path]:
    if pages_per_part <= 0:
        return [path]
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception:
        from PyPDF2 import PdfReader, PdfWriter

    output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    if total_pages <= pages_per_part:
        return [path]

    parts: list[Path] = []
    for start in range(0, total_pages, pages_per_part):
        end = min(start + pages_per_part, total_pages)
        writer = PdfWriter()
        for page_index in range(start, end):
            writer.add_page(reader.pages[page_index])
        part_path = output_dir / f"{path.stem}-part-{len(parts) + 1:03d}-p{start + 1}-{end}.pdf"
        with part_path.open("wb") as handle:
            writer.write(handle)
        parts.append(part_path)
    return parts


def project_path(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    env_value = os.getenv("OBSIDIAN_LLM_WIKI_PROJECT")
    if env_value:
        return Path(env_value).resolve()
    return Path(__file__).resolve().parents[4]


def run_cli(project: Path, args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "obsidian_llm_wiki.cli", *args]
    merged_env = os.environ.copy()
    merged_env.setdefault("PYTHONUTF8", "1")
    merged_env.setdefault("PYTHONIOENCODING", "utf-8")
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=str(project),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=merged_env,
    )


def base_report(command: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": now_id(command),
        "command": command,
        "status": "success",
        "started_at": utc_now(),
        "finished_at": "",
        "inputs": json_safe(inputs),
        "environment": {},
        "results": {},
        "generated_files": [],
        "updated_files": [],
        "skipped": [],
        "errors": [],
        "next_paths": [],
    }


def write_report(vault: Path, report: dict[str, Any]) -> None:
    report["finished_at"] = utc_now()
    base = vault / "logs" / "skill-runs"
    json_path = base / f"{report['run_id']}.json"
    md_path = base / f"{report['run_id']}.md"
    report["report_json"] = str(json_path)
    report["report_markdown"] = str(md_path)
    report = json_safe(report)
    dump_json(json_path, report)

    lines = [
        f"# {report['command']} report",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- status: `{report['status']}`",
        f"- started_at: `{report['started_at']}`",
        f"- finished_at: `{report['finished_at']}`",
        "",
        "## Inputs",
        "",
    ]
    for key, value in report.get("inputs", {}).items():
        lines.append(f"- {key}: `{value}`")
    for section in ["results", "generated_files", "updated_files", "skipped", "errors", "next_paths"]:
        lines.extend(["", f"## {section}", ""])
        value = report.get(section)
        if not value:
            lines.append("- none")
        elif isinstance(value, dict):
            for key, item in value.items():
                lines.append(f"- {key}: `{json.dumps(item, ensure_ascii=False)}`")
        else:
            for item in value:
                rendered = json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
                lines.append(f"- `{rendered}`")
    write_text(md_path, "\n".join(lines) + "\n")


def finish(report: dict[str, Any], vault: Path) -> None:
    if report["errors"] and report["status"] == "success":
        report["status"] = "failed"
    report = json_safe(report)
    write_report(vault, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def parse_key_value_stdout(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in {"source_id", "status", "page", "topics", "entities", "mode", "message", "rebuilt", "sources"}:
            result[key] = value.strip()
    return result


def vault_relative(path: Path, vault: Path) -> str:
    return str(path.relative_to(vault)).replace("/", "\\")


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "untitled"


def normalize_term_key(value: str) -> str:
    return clean_text(value).casefold()


def is_managed_page(path: Path) -> bool:
    if not path.exists():
        return False
    text = read_text(path)
    return text.startswith("---") and "managed: true" in text.lower()


def project_language(vault: Path) -> str:
    return clean_text(load_config(vault).get("language")) or "zh"


def source_page_path(vault: Path, source_id: str, title: str, cache: dict[str, Any]) -> Path:
    sources_dir = vault / "wiki" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(title) or source_id
    current = cache.get("sources", {}).get(source_id, {}).get("source_page")
    current_path = vault / current if current else None
    target = sources_dir / f"{slug}.md"
    if target.exists() and target != current_path:
        target = sources_dir / f"{slug}-{source_id[:8]}.md"
    if current_path and current_path != target and current_path.exists() and is_managed_page(current_path):
        current_path.unlink()
    return target


def topic_page_path(vault: Path, topic: str) -> Path:
    path = vault / "wiki" / "topics" / f"{slugify(topic)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def entity_page_path(vault: Path, entity: str) -> Path:
    path = vault / "wiki" / "entities" / f"{slugify(entity)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def topic_digest_path(vault: Path, topic: str) -> Path:
    path = vault / "derived" / "topics" / f"{slugify(topic)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def entity_digest_path(vault: Path, entity: str) -> Path:
    path = vault / "derived" / "entities" / f"{slugify(entity)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def wiki_link(path: Path, vault: Path, label: str) -> str:
    rel = path.relative_to(vault).as_posix()
    return f"[[{rel}|{label}]]"


def page_title(path: Path) -> str:
    if not path.exists():
        return path.stem
    text = read_text(path)
    match = re.search(r"(?mi)^title:\s*(.+?)\s*$", text)
    if match:
        return clean_text(match.group(1)).strip('"')
    for line in text.splitlines():
        if line.startswith("# "):
            return clean_text(line[2:])
    return path.stem


def find_source_id(vault: Path, source_id: str | None, source_page: str | None) -> str:
    cache = load_cache(vault)
    if source_id:
        if source_id not in cache.get("sources", {}):
            raise ValueError(f"source_id not found: {source_id}")
        return source_id
    if source_page:
        normalized = source_page.replace("/", "\\").lower().removesuffix(".md")
        for sid, item in cache.get("sources", {}).items():
            page = str(item.get("source_page", "")).replace("/", "\\").lower().removesuffix(".md")
            if page == normalized or page.endswith(normalized):
                return sid
    raise ValueError("Provide --source-id or --source-page")


def get_source_paths(vault: Path, source_id: str, source: dict[str, Any]) -> tuple[Path, Path]:
    derived_md_rel = str(source.get("derived_markdown_path") or f"derived\\{source_id}\\content.md").strip()
    derived_json_rel = str(source.get("derived_json_path") or f"derived\\{source_id}\\content.json").strip()
    return vault / derived_md_rel, vault / derived_json_rel


def ensure_source_record(vault: Path, source_id: str, cache: dict[str, Any]) -> dict[str, Any]:
    sources = cache.setdefault("sources", {})
    source = sources.get(source_id)
    if isinstance(source, dict):
        return source
    derived_md = vault / "derived" / source_id / "content.md"
    derived_json = vault / "derived" / source_id / "content.json"
    source = {
        "source_id": source_id,
        "title": source_id,
        "source_type": "",
        "ingested_at": "",
        "original_path": "",
        "raw_path": "",
        "derived_markdown_path": vault_relative(derived_md, vault),
        "derived_json_path": vault_relative(derived_json, vault),
        "tags": [],
    }
    sources[source_id] = source
    return source


def section_for_line(path: Path, line_number: int) -> str:
    if not path.exists():
        return "unknown"
    heading = "unknown"
    for line in read_text(path).splitlines()[: max(0, line_number)]:
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
    if heading in SOURCE_SECTION_NAMES:
        return f"source:{heading}"
    if heading in TOPIC_SECTION_NAMES:
        return f"topic:{heading}"
    if heading in ENTITY_SECTION_NAMES:
        return f"entity:{heading}"
    return heading


def ingest_env(structure: bool, mineru_timeout: int | None, digest_engine: str) -> dict[str, str] | None:
    updates: dict[str, str] = {}
    if not structure or digest_engine == "codex":
        updates["LLM_WIKI_MODEL"] = ""
    if mineru_timeout:
        updates["MINERU_TIMEOUT_SECONDS"] = str(mineru_timeout)
    return updates or None


def normalize_source_digest(payload: dict[str, Any], source_id: str | None = None, strict: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("digest payload must be a JSON object")
    if source_id and clean_text(payload.get("source_id")) and clean_text(payload.get("source_id")) != source_id:
        raise ValueError(f"digest source_id mismatch: expected {source_id}")

    final_source_id = source_id or clean_text(payload.get("source_id"))
    title = clean_text(payload.get("title") or payload.get("canonical_title"))
    canonical_title = clean_text(payload.get("canonical_title") or payload.get("title"))
    knowledge_type = clean_text(payload.get("knowledge_type"))
    source_language = clean_text(payload.get("source_language"))

    background = first_non_empty_list(payload.get("background"))
    treatment = first_non_empty_list(
        payload.get("treatment"),
        payload.get("methods"),
        payload.get("identification"),
        payload.get("data_and_sample"),
        payload.get("variable_measurement"),
    )
    details = first_non_empty_list(
        payload.get("details"),
        payload.get("key_details"),
        payload.get("mechanisms"),
        payload.get("robustness"),
        payload.get("heterogeneity"),
        payload.get("limitations"),
        payload.get("research_questions"),
    )
    results_and_contribution = first_non_empty_list(
        payload.get("results_and_contribution"),
        payload.get("results"),
        payload.get("contribution"),
    )

    if strict:
        if not final_source_id:
            raise ValueError("digest must contain source_id")
        if not title:
            raise ValueError("digest must contain title or canonical_title")
        if not canonical_title:
            raise ValueError("digest must contain canonical_title or title")
        if not knowledge_type:
            raise ValueError("digest must contain knowledge_type")
        if not source_language:
            raise ValueError("digest must contain source_language")
        background = normalize_string_list(background, "background")
        treatment = normalize_string_list(treatment, "treatment")
        details = normalize_string_list(details, "details")
        results_and_contribution = normalize_string_list(results_and_contribution, "results_and_contribution")
        topics = normalize_string_list(payload.get("topics"), "topics")
        entities = normalize_string_list(payload.get("entities"), "entities")
    else:
        topics = merge_unique_lists(payload.get("topics"))
        entities = merge_unique_lists(payload.get("entities"))

    normalized = {
        "source_id": final_source_id,
        "title": title,
        "canonical_title": canonical_title,
        "knowledge_type": knowledge_type,
        "source_language": source_language,
        "background": background,
        "treatment": treatment,
        "details": details,
        "results_and_contribution": results_and_contribution,
        "topics": topics,
        "entities": entities,
        "structured_at": clean_text(payload.get("structured_at")) or utc_now(),
    }

    for field in SOURCE_INTERNAL_OPTIONAL_LIST_FIELDS:
        values = merge_unique_lists(payload.get(field))
        if values:
            normalized[field] = values
    for field in ["role_for_purpose", "derived_markdown_path", "derived_json_path", "digest_path"]:
        value = clean_text(payload.get(field))
        if value:
            normalized[field] = value
    return normalized


def validate_digest_payload(payload: dict[str, Any], source_id: str) -> dict[str, Any]:
    return normalize_source_digest(payload, source_id=source_id, strict=True)


def normalize_topic_digest(payload: dict[str, Any], topic: str | None = None, strict: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("topic payload must be a JSON object")
    payload_topic = clean_text(payload.get("topic") or payload.get("title"))
    final_topic = topic or payload_topic
    if topic and payload_topic and normalize_term_key(payload_topic) != normalize_term_key(topic):
        raise ValueError(f"topic mismatch: expected {topic}")
    title = clean_text(payload.get("title") or final_topic)
    background = first_non_empty_list(payload.get("background"))
    treatment = first_non_empty_list(payload.get("treatment"), payload.get("treatment_and_method"))
    details = first_non_empty_list(payload.get("details"), payload.get("definition"))
    results_and_contribution = first_non_empty_list(
        payload.get("results_and_contribution"),
        payload.get("findings_and_contribution"),
    )
    source_ids = payload.get("source_ids")
    if strict:
        if not final_topic:
            raise ValueError("topic payload must contain topic or title")
        background = normalize_string_list(background, "background")
        treatment = normalize_string_list(treatment, "treatment")
        details = normalize_string_list(details, "details")
        results_and_contribution = normalize_string_list(results_and_contribution, "results_and_contribution")
        source_ids = normalize_string_list(source_ids, "source_ids")
    else:
        source_ids = merge_unique_lists(source_ids)
    normalized = {
        "topic": final_topic,
        "title": title or final_topic,
        "background": background,
        "treatment": treatment,
        "details": details,
        "results_and_contribution": results_and_contribution,
        "source_ids": source_ids,
        "structured_at": clean_text(payload.get("structured_at")) or utc_now(),
    }
    for field in TOPIC_INTERNAL_OPTIONAL_LIST_FIELDS:
        values = merge_unique_lists(payload.get(field))
        if values:
            normalized[field] = values
    return normalized


def validate_topic_payload(payload: dict[str, Any], topic: str) -> dict[str, Any]:
    return normalize_topic_digest(payload, topic=topic, strict=True)


def normalize_entity_digest(payload: dict[str, Any], entity: str | None = None, strict: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("entity payload must be a JSON object")
    payload_entity = clean_text(payload.get("entity") or payload.get("title"))
    final_entity = entity or payload_entity
    if entity and payload_entity and normalize_term_key(payload_entity) != normalize_term_key(entity):
        raise ValueError(f"entity mismatch: expected {entity}")
    title = clean_text(payload.get("title") or final_entity)
    background = first_non_empty_list(payload.get("background"), payload.get("definition"))
    treatment = first_non_empty_list(payload.get("treatment"), payload.get("measurement_and_identification"))
    details = first_non_empty_list(payload.get("details"), payload.get("definition"))
    results_and_contribution = first_non_empty_list(
        payload.get("results_and_contribution"),
        payload.get("role_in_results"),
    )
    source_ids = payload.get("source_ids")
    if strict:
        if not final_entity:
            raise ValueError("entity payload must contain entity or title")
        background = normalize_string_list(background, "background")
        treatment = normalize_string_list(treatment, "treatment")
        details = normalize_string_list(details, "details")
        results_and_contribution = normalize_string_list(results_and_contribution, "results_and_contribution")
        source_ids = normalize_string_list(source_ids, "source_ids")
    else:
        source_ids = merge_unique_lists(source_ids)
    normalized = {
        "entity": final_entity,
        "title": title or final_entity,
        "background": background,
        "treatment": treatment,
        "details": details,
        "results_and_contribution": results_and_contribution,
        "source_ids": source_ids,
        "structured_at": clean_text(payload.get("structured_at")) or utc_now(),
    }
    for field in ENTITY_INTERNAL_OPTIONAL_LIST_FIELDS:
        values = merge_unique_lists(payload.get(field))
        if values:
            normalized[field] = values
    return normalized


def validate_entity_payload(payload: dict[str, Any], entity: str) -> dict[str, Any]:
    return normalize_entity_digest(payload, entity=entity, strict=True)


def find_existing_term_page(vault: Path, term: str, kind: str, cache: dict[str, Any]) -> Path | None:
    page_map_key = "topic_pages" if kind == "topic" else "entity_pages"
    for item in cache.get(page_map_key, {}).values():
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get(kind))
        if normalize_term_key(name) != normalize_term_key(term):
            continue
        page_rel = clean_text(item.get("page_path"))
        if not page_rel:
            continue
        page_path = vault / page_rel
        if page_path.exists():
            return page_path
    candidate = topic_page_path(vault, term) if kind == "topic" else entity_page_path(vault, term)
    if candidate.exists():
        return candidate
    return None


def link_terms(vault: Path, cache: dict[str, Any], values: list[str], kind: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = clean_text(value)
        if not term:
            continue
        page_path = find_existing_term_page(vault, term, kind, cache)
        if not page_path:
            continue
        link = wiki_link(page_path, vault, page_title(page_path))
        if link in seen:
            continue
        seen.add(link)
        links.append(f"- {link}")
    return links or ["- 暂无内容"]


def related_source_links(vault: Path, cache: dict[str, Any], source_ids: list[str]) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for source_id in source_ids:
        source = cache.get("sources", {}).get(source_id)
        if not isinstance(source, dict):
            continue
        page_rel = clean_text(source.get("source_page"))
        if not page_rel:
            continue
        page_path = vault / page_rel
        if not page_path.exists():
            continue
        title = clean_text(source.get("title") or source_id)
        link = wiki_link(page_path, vault, title)
        if link in seen:
            continue
        seen.add(link)
        links.append(f"- {link}")
    return links or ["- 暂无内容"]


def render_source_page(vault: Path, cache: dict[str, Any], source_id: str, title: str, digest: dict[str, Any]) -> str:
    normalized = normalize_source_digest(digest, source_id=source_id, strict=False)
    lines = [
        "---",
        "managed: true",
        "page_kind: source",
        f"source_id: {source_id}",
        f"title: {title}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    for heading, field_name in SOURCE_SECTIONS:
        values = normalized.get(field_name, [])
        if not values:
            continue
        lines.extend([f"## {heading}", "", *as_bullets(values), ""])
    lines.extend(["## 相关主题", "", *link_terms(vault, cache, list(normalized.get("topics") or []), "topic"), ""])
    lines.extend(["## 相关实体", "", *link_terms(vault, cache, list(normalized.get("entities") or []), "entity"), ""])
    return "\n".join(lines)


def render_topic_page(vault: Path, cache: dict[str, Any], topic: str, digest: dict[str, Any]) -> str:
    normalized = normalize_topic_digest(digest, topic=topic, strict=False)
    title = clean_text(normalized.get("title") or topic) or topic
    lines = [
        "---",
        "managed: true",
        "page_kind: topic",
        f"title: {title}",
        f"topic: {topic}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    for heading, field_name in TOPIC_SECTIONS:
        values = normalized.get(field_name, [])
        if not values:
            continue
        lines.extend([f"## {heading}", "", *as_bullets(values), ""])
    lines.extend(["## 相关来源", "", *related_source_links(vault, cache, list(normalized.get("source_ids") or [])), ""])
    return "\n".join(lines)


def render_entity_page(vault: Path, cache: dict[str, Any], entity: str, digest: dict[str, Any]) -> str:
    normalized = normalize_entity_digest(digest, entity=entity, strict=False)
    title = clean_text(normalized.get("title") or entity) or entity
    lines = [
        "---",
        "managed: true",
        "page_kind: entity",
        f"title: {title}",
        f"entity: {entity}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    for heading, field_name in ENTITY_SECTIONS:
        values = normalized.get(field_name, [])
        if not values:
            continue
        lines.extend([f"## {heading}", "", *as_bullets(values), ""])
    lines.extend(["## 相关来源", "", *related_source_links(vault, cache, list(normalized.get("source_ids") or [])), ""])
    return "\n".join(lines)


def rewrite_overview_page(vault: Path, cache: dict[str, Any]) -> dict[str, int]:
    overview_path = vault / "wiki" / "overview.md"
    topics_dir = vault / "wiki" / "topics"
    entities_dir = vault / "wiki" / "entities"
    config = load_config(vault)

    topic_files = sorted(topics_dir.glob("*.md"), key=lambda p: p.name.casefold())
    entity_files = sorted(entities_dir.glob("*.md"), key=lambda p: p.name.casefold())

    source_items: list[tuple[str, str, Path]] = []
    for source_id, source in cache.get("sources", {}).items():
        if not isinstance(source, dict):
            continue
        page_rel = clean_text(source.get("source_page"))
        if not page_rel:
            continue
        page_path = vault / page_rel
        if not page_path.exists():
            continue
        title = clean_text(source.get("title") or source_id)
        ingested_at = clean_text(source.get("ingested_at"))
        source_items.append((ingested_at, title, page_path))
    source_items.sort(key=lambda item: item[0], reverse=True)
    thesis_sections = [
        ("论文工作面", "core"),
        ("文献桥接", "literature"),
        ("识别设计", "identification"),
        ("章节草稿", "drafts"),
    ]

    title = clean_text(config.get("title")) or "LLM Wiki"
    purpose = vault_purpose(vault)
    lines = [
        "# 知识库总览",
        "",
        f"- 标题：{title}",
        f"- 用途：{purpose}",
        "- 引擎：Codex（知识消化、结构整理、页面生成）",
        f"- 来源数：{len(source_items)}",
        f"- 主题数：{len(topic_files)}",
        f"- 实体数：{len(entity_files)}",
        "",
    ]
    for heading, folder in thesis_sections:
        directory = vault / "wiki" / folder
        pages = sorted(directory.glob("*.md"), key=lambda p: p.name.casefold()) if directory.exists() else []
        if not pages:
            continue
        lines.extend([f"## {heading}", ""])
        for page_path in pages[:8]:
            lines.append(f"- {wiki_link(page_path, vault, page_title(page_path))}")
        if len(pages) > 8:
            lines.append(f"- 其余 {len(pages) - 8} 个页面请查看 `wiki/{folder}/`")
        lines.append("")
    lines.extend(["## 最新来源", ""])
    if source_items:
        for _, item_title, page_path in source_items[:10]:
            lines.append(f"- {wiki_link(page_path, vault, item_title)}")
    else:
        lines.append("- 暂无内容")

    lines.extend(["", "## 主题索引", ""])
    if topic_files:
        for page_path in topic_files[:30]:
            lines.append(f"- {wiki_link(page_path, vault, page_title(page_path))}")
        if len(topic_files) > 30:
            lines.append(f"- 其余 {len(topic_files) - 30} 个主题请查看 `wiki/topics/`")
    else:
        lines.append("- 暂无内容")

    lines.extend(["", "## 实体索引", ""])
    if entity_files:
        for page_path in entity_files[:40]:
            lines.append(f"- {wiki_link(page_path, vault, page_title(page_path))}")
        if len(entity_files) > 40:
            lines.append(f"- 其余 {len(entity_files) - 40} 个实体请查看 `wiki/entities/`")
    else:
        lines.append("- 暂无内容")

    write_text(overview_path, "\n".join(lines) + "\n")
    return {"topics": len(topic_files), "entities": len(entity_files), "sources": len(source_items)}


def rewrite_source_pages(vault: Path, cache: dict[str, Any], source_ids: list[str] | None = None) -> int:
    rewritten = 0
    ids = source_ids or list(cache.get("sources", {}).keys())
    for source_id in ids:
        source = cache.get("sources", {}).get(source_id)
        if not isinstance(source, dict):
            continue
        digest_rel = clean_text(source.get("digest_path")) or f"derived\\{source_id}\\digest.json"
        digest_path = vault / digest_rel
        if not digest_path.exists():
            continue
        raw_digest = load_json(digest_path, {})
        if not isinstance(raw_digest, dict):
            continue
        digest = normalize_source_digest(raw_digest, source_id=source_id, strict=False)
        title = clean_text(digest.get("canonical_title") or digest.get("title") or source.get("title") or source_id)
        page_path = source_page_path(vault, source_id, title, cache)
        write_text(page_path, render_source_page(vault, cache, source_id, title, digest))
        source["source_page"] = vault_relative(page_path, vault)
        source["title"] = title
        rewritten += 1
    return rewritten


def rewrite_index_pages(vault: Path, cache: dict[str, Any], kind: str) -> int:
    page_map_key = "topic_pages" if kind == "topic" else "entity_pages"
    rewritten = 0
    for item in cache.get(page_map_key, {}).values():
        if not isinstance(item, dict):
            continue
        digest_rel = clean_text(item.get("digest_path"))
        page_rel = clean_text(item.get("page_path"))
        name = clean_text(item.get(kind))
        if not digest_rel or not page_rel or not name:
            continue
        digest_path = vault / digest_rel
        page_path = vault / page_rel
        if not digest_path.exists():
            continue
        digest = load_json(digest_path, {})
        if not isinstance(digest, dict):
            continue
        if kind == "topic":
            write_text(page_path, render_topic_page(vault, cache, name, digest))
        else:
            write_text(page_path, render_entity_page(vault, cache, name, digest))
        rewritten += 1
    return rewritten


def is_legacy_generated_index_page(path: Path, kind: str) -> bool:
    if not path.exists():
        return False
    text = read_text(path)
    if is_managed_page(path):
        return False
    legacy_markers = {
        "topic": ["## 定义", "## 在论文中的作用", "## 写作用途", "## 相关来源", "## 相关证据"],
        "entity": ["## 定义", "## 为什么重要", "## 写作提示", "## 相关来源", "## 证据锚点"],
    }
    markers = legacy_markers[kind]
    return all(marker in text for marker in markers)


def prune_untracked_index_pages(vault: Path, cache: dict[str, Any], kind: str) -> int:
    directory = vault / "wiki" / ("topics" if kind == "topic" else "entities")
    tracked_key = "topic_pages" if kind == "topic" else "entity_pages"
    tracked_paths = {
        (vault / clean_text(item.get("page_path"))).resolve()
        for item in cache.get(tracked_key, {}).values()
        if isinstance(item, dict) and clean_text(item.get("page_path"))
    }
    removed = 0
    for path in directory.glob("*.md"):
        resolved = path.resolve()
        if resolved in tracked_paths:
            continue
        if is_legacy_generated_index_page(path, kind):
            path.unlink()
            removed += 1
    return removed


def prepare_source_bundle_paths(vault: Path, source_id: str, output: str | None, prompt_output: str | None) -> tuple[Path, Path]:
    bundle_path = Path(output).resolve() if output else (vault / "logs" / "codex-digest-bundles" / f"{source_id}.json")
    prompt_path = Path(prompt_output).resolve() if prompt_output else (vault / "logs" / "codex-digest-bundles" / f"{source_id}.prompt.md")
    return bundle_path, prompt_path


def prepare_index_bundle_paths(vault: Path, kind: str, term: str, output: str | None, prompt_output: str | None) -> tuple[Path, Path]:
    base = vault / "logs" / "codex-index-bundles" / f"{kind}s"
    bundle_path = Path(output).resolve() if output else (base / f"{slugify(term)}.json")
    prompt_path = Path(prompt_output).resolve() if prompt_output else (base / f"{slugify(term)}.prompt.md")
    return bundle_path, prompt_path


def build_source_digest_prompt(vault: Path, bundle_path: Path, prompt_path: Path, digest_output_path: Path, bundle: dict[str, Any]) -> str:
    title = clean_text(bundle.get("source_record", {}).get("title") or bundle.get("source_id"))
    purpose = bundle["purpose"]
    language = project_language(vault)
    fields_json = json.dumps(
        {
            "source_id": bundle["source_id"],
            "title": title,
            "canonical_title": title,
            "knowledge_type": "paper|policy|method-note|data-note|general",
            "source_language": language,
            "background": ["..."],
            "treatment": ["..."],
            "details": ["..."],
            "results_and_contribution": ["..."],
            "topics": ["..."],
            "entities": ["..."],
        },
        ensure_ascii=False,
        indent=2,
    )
    return "\n".join(
        [
            "# Codex Source Digest Prompt",
            "",
            "请读取下面的 bundle.json，并为该来源生成 `digest.json`。",
            "",
            f"- bundle.json: `{bundle_path}`",
            f"- prompt.md: `{prompt_path}`",
            f"- 建议输出路径: `{digest_output_path}`",
            f"- source_id: `{bundle['source_id']}`",
            f"- 标题参考: `{title}`",
            f"- 知识库用途: `{purpose}`",
            "",
            "硬性要求：",
            "",
            "- 先理解 `purpose`，再决定如何提炼该来源的重点。",
            "- 以 `content.json` 为主，以 `content.md` 为辅。",
            "- 输出必须是纯 JSON 对象，不要加 Markdown 代码块，不要加解释文字。",
            "- 这是整篇消化，不是短摘要。四个字段都要把事情讲清楚，不要求字数相同，但不能短到失去信息。",
            "- `背景` 要说明研究问题、情境、动机、对象。",
            "- `处理` 要说明怎么做，包含识别、方法、数据、变量或实验设计等核心做法。",
            "- `细节` 要说明为什么这么做，包含关键假设、机制、方法选择理由、限制与重要解释点。",
            "- `结果与贡献` 要说明发现了什么、与既有研究相比贡献是什么、对当前知识主线提供了什么增量。",
            "- `topics` 和 `entities` 保持短语列表，不要写成长句。",
            "- 不要把目录、封面、学校信息、作者信息、DOI、页眉页脚、关键词栏等噪声写进 digest。",
            "",
            "输出字段至少包含：",
            "",
            "```json",
            fields_json,
            "```",
            "",
        ]
    )


def build_digest_bundle(vault: Path, source_id: str, output: str | None = None, prompt_output: str | None = None) -> tuple[Path, Path, dict[str, Any]]:
    cache = load_cache(vault)
    source = ensure_source_record(vault, source_id, cache)
    derived_markdown, derived_json = get_source_paths(vault, source_id, source)
    if not derived_json.exists():
        raise FileNotFoundError(f"Missing parsed JSON: {derived_json}")
    if not derived_markdown.exists():
        raise FileNotFoundError(f"Missing parsed Markdown: {derived_markdown}")

    bundle_path, prompt_path = prepare_source_bundle_paths(vault, source_id, output, prompt_output)
    digest_output = vault / "derived" / source_id / "digest.json"
    bundle = {
        "source_id": source_id,
        "generated_at": utc_now(),
        "vault_path": str(vault),
        "purpose": vault_purpose(vault),
        "source_record": json_safe(source),
        "derived": {
            "content_json_path": str(derived_json),
            "content_markdown_path": str(derived_markdown),
            "content_json": load_json(derived_json, {}),
            "content_markdown": read_text(derived_markdown),
        },
        "digest_contract": {
            "required_string_fields": ["source_id", "title", "canonical_title", "knowledge_type", "source_language"],
            "required_list_fields": SOURCE_REQUIRED_LIST_FIELDS,
            "output_path": str(digest_output),
        },
        "page_contract": {
            "visible_sections": [heading for heading, _ in SOURCE_SECTIONS],
            "link_sections": ["相关主题", "相关实体"],
        },
        "notes": {
            "primary_input": "content.json",
            "secondary_input": "content.md",
            "workflow": "semi-automatic codex digest",
        },
    }
    dump_json(bundle_path, bundle)
    write_text(prompt_path, build_source_digest_prompt(vault, bundle_path, prompt_path, digest_output, bundle))
    return bundle_path, prompt_path, bundle


def collect_index_sources(vault: Path, cache: dict[str, Any], field_name: str, term: str) -> list[dict[str, Any]]:
    normalized_term = normalize_term_key(term)
    rows: list[dict[str, Any]] = []
    for source_id, source in cache.get("sources", {}).items():
        if not isinstance(source, dict):
            continue
        digest_rel = clean_text(source.get("digest_path")) or f"derived\\{source_id}\\digest.json"
        digest_path = vault / digest_rel
        if not digest_path.exists():
            continue
        raw_digest = load_json(digest_path, {})
        if not isinstance(raw_digest, dict):
            continue
        digest = normalize_source_digest(raw_digest, source_id=source_id, strict=False)
        terms = [normalize_term_key(item) for item in list(digest.get(field_name) or [])]
        if normalized_term not in terms:
            continue
        rows.append(
            {
                "source_id": source_id,
                "title": clean_text(digest.get("canonical_title") or digest.get("title") or source.get("title") or source_id),
                "source_page": clean_text(source.get("source_page")),
                "digest_path": str(digest_path),
                "background": digest.get("background", []),
                "treatment": digest.get("treatment", []),
                "details": digest.get("details", []),
                "results_and_contribution": digest.get("results_and_contribution", []),
                "topics": digest.get("topics", []),
                "entities": digest.get("entities", []),
            }
        )
    return rows


def build_topic_prompt(vault: Path, bundle_path: Path, prompt_path: Path, digest_output_path: Path, bundle: dict[str, Any]) -> str:
    fields_json = json.dumps(
        {
            "topic": bundle["topic"],
            "title": bundle["topic"],
            "background": ["..."],
            "treatment": ["..."],
            "details": ["..."],
            "results_and_contribution": ["..."],
            "source_ids": [row["source_id"] for row in bundle["supporting_sources"]],
        },
        ensure_ascii=False,
        indent=2,
    )
    return "\n".join(
        [
            "# Codex Topic Digest Prompt",
            "",
            "请读取下面的 topic bundle，并输出纯 JSON。",
            "",
            f"- bundle.json: `{bundle_path}`",
            f"- prompt.md: `{prompt_path}`",
            f"- 建议输出路径: `{digest_output_path}`",
            f"- topic: `{bundle['topic']}`",
            f"- 知识库用途: `{bundle['purpose']}`",
            "",
            "硬性要求：",
            "",
            "- 先理解 `purpose`，再决定这个主题在当前知识主线里的重点。",
            "- 只根据 `supporting_sources` 中已有来源 digest 来综合，不要凭空外推。",
            "- 输出必须是纯 JSON 对象，不要加 Markdown 代码块，不要加解释文字。",
            "- 这是主题消化，不是概念卡片。四个字段都要把主题如何贯穿多篇来源讲清楚。",
            "- `背景` 说明该主题为什么会反复出现，它解决什么问题或回应什么研究背景。",
            "- `处理` 说明相关来源通常怎样处理这个主题，包含识别、方法、数据、设计或分析路径。",
            "- `细节` 说明为什么这样处理，包含关键假设、机制、细微差异、重要限制与解释点。",
            "- `结果与贡献` 说明相关来源围绕该主题的主要发现、理论或方法贡献，以及对当前知识主线的意义。",
            "- `source_ids` 只保留真实支持该主题的来源编号。",
            "",
            "输出字段至少包含：",
            "",
            "```json",
            fields_json,
            "```",
            "",
        ]
    )


def build_topic_bundle(vault: Path, topic: str, output: str | None = None, prompt_output: str | None = None) -> tuple[Path, Path, dict[str, Any]]:
    cache = load_cache(vault)
    supporting_sources = collect_index_sources(vault, cache, "topics", topic)
    if not supporting_sources:
        raise ValueError(f"No digested sources found for topic: {topic}")
    bundle_path, prompt_path = prepare_index_bundle_paths(vault, "topic", topic, output, prompt_output)
    digest_output = topic_digest_path(vault, topic)
    bundle = {
        "kind": "topic",
        "topic": topic,
        "generated_at": utc_now(),
        "vault_path": str(vault),
        "purpose": vault_purpose(vault),
        "supporting_sources": supporting_sources,
        "digest_contract": {
            "required_string_fields": ["topic", "title"],
            "required_list_fields": TOPIC_REQUIRED_LIST_FIELDS,
            "output_path": str(digest_output),
        },
        "page_contract": {
            "visible_sections": [heading for heading, _ in TOPIC_SECTIONS] + ["相关来源"],
        },
    }
    dump_json(bundle_path, bundle)
    write_text(prompt_path, build_topic_prompt(vault, bundle_path, prompt_path, digest_output, bundle))
    return bundle_path, prompt_path, bundle


def build_entity_prompt(vault: Path, bundle_path: Path, prompt_path: Path, digest_output_path: Path, bundle: dict[str, Any]) -> str:
    fields_json = json.dumps(
        {
            "entity": bundle["entity"],
            "title": bundle["entity"],
            "background": ["..."],
            "treatment": ["..."],
            "details": ["..."],
            "results_and_contribution": ["..."],
            "source_ids": [row["source_id"] for row in bundle["supporting_sources"]],
        },
        ensure_ascii=False,
        indent=2,
    )
    return "\n".join(
        [
            "# Codex Entity Digest Prompt",
            "",
            "请读取下面的 entity bundle，并输出纯 JSON。",
            "",
            f"- bundle.json: `{bundle_path}`",
            f"- prompt.md: `{prompt_path}`",
            f"- 建议输出路径: `{digest_output_path}`",
            f"- entity: `{bundle['entity']}`",
            f"- 知识库用途: `{bundle['purpose']}`",
            "",
            "硬性要求：",
            "",
            "- 先理解 `purpose`，再决定这个实体在当前知识主线里的重点。",
            "- 只根据 `supporting_sources` 中已有来源 digest 来综合，不要凭空外推。",
            "- 输出必须是纯 JSON 对象，不要加 Markdown 代码块，不要加解释文字。",
            "- 这不是概念卡片。四个字段都要把该实体在多篇来源中的使用背景、处理方式和研究意义讲清楚。",
            "- `背景` 说明这个实体在当前知识主线中的问题背景与使用背景，而不是泛泛定义。",
            "- `处理` 说明相关来源怎样测度、识别、估计或操作化这个实体。",
            "- `细节` 说明为什么这样处理，包含关键假设、口径差异、解释边界与重要细节。",
            "- `结果与贡献` 说明该实体如何进入结果解释、贡献表述以及对当前知识主线的价值。",
            "- `source_ids` 只保留真实支持该实体的来源编号。",
            "",
            "输出字段至少包含：",
            "",
            "```json",
            fields_json,
            "```",
            "",
        ]
    )


def build_entity_bundle(vault: Path, entity: str, output: str | None = None, prompt_output: str | None = None) -> tuple[Path, Path, dict[str, Any]]:
    cache = load_cache(vault)
    supporting_sources = collect_index_sources(vault, cache, "entities", entity)
    if not supporting_sources:
        raise ValueError(f"No digested sources found for entity: {entity}")
    bundle_path, prompt_path = prepare_index_bundle_paths(vault, "entity", entity, output, prompt_output)
    digest_output = entity_digest_path(vault, entity)
    bundle = {
        "kind": "entity",
        "entity": entity,
        "generated_at": utc_now(),
        "vault_path": str(vault),
        "purpose": vault_purpose(vault),
        "supporting_sources": supporting_sources,
        "digest_contract": {
            "required_string_fields": ["entity", "title"],
            "required_list_fields": ENTITY_REQUIRED_LIST_FIELDS,
            "output_path": str(digest_output),
        },
        "page_contract": {
            "visible_sections": [heading for heading, _ in ENTITY_SECTIONS] + ["相关来源"],
        },
    }
    dump_json(bundle_path, bundle)
    write_text(prompt_path, build_entity_prompt(vault, bundle_path, prompt_path, digest_output, bundle))
    return bundle_path, prompt_path, bundle


def maybe_prepare_digest_bundle(vault: Path, source_id: str, report: dict[str, Any]) -> None:
    bundle_path, prompt_path, _ = build_digest_bundle(vault, source_id)
    report["generated_files"].extend([str(bundle_path), str(prompt_path)])
    report["next_paths"].extend([str(bundle_path), str(prompt_path)])


def command_init_vault(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("init-vault", vars(args))
    project = project_path(args.project)
    completed = run_cli(project, ["init", str(vault), "--title", args.title, "--language", args.language, "--purpose", args.purpose])
    report["environment"] = {"project": str(project), "vault": str(vault)}
    report["results"]["returncode"] = completed.returncode
    report["results"]["stdout"] = completed.stdout.strip()
    if completed.returncode != 0:
        report["status"] = "failed"
        report["errors"].append({"stage": "init", "stderr": completed.stderr[-3000:]})
    else:
        report["generated_files"].extend([str(vault / ".wiki-config.json"), str(vault / ".wiki-cache.json")])
        report["next_paths"].append(str(vault / "wiki" / "overview.md"))
    finish(report, vault)


def command_init_thesis_workspace(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("init-thesis-workspace", vars(args))
    cache = load_cache(vault)
    created: list[str] = []
    skipped: list[str] = []
    for rel_path, text in THESIS_STARTER_PAGES.items():
        path = vault / "wiki" / Path(rel_path)
        if path.exists() and not args.force:
            skipped.append(str(path))
            continue
        write_text(path, text if text.endswith("\n") else text + "\n")
        created.append(str(path))
    rewrite_overview_page(vault, cache)
    report["generated_files"].extend(created)
    report["skipped"].extend(skipped)
    report["updated_files"].append(str(vault / "wiki" / "overview.md"))
    report["next_paths"].append(str(vault / "wiki" / "overview.md"))
    finish(report, vault)


def command_ingest_file(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("ingest-file", vars(args))
    project = project_path(args.project)
    source_file = Path(args.file).resolve()
    split_dir = vault / "logs" / "skill-runs" / f"{report['run_id']}-pdf-parts"
    parts = split_pdf(source_file, split_dir, args.split_pages) if source_file.suffix.lower() == ".pdf" else [source_file]
    report["environment"] = {
        "project": str(project),
        "vault": str(vault),
        "pdf_parser": "MinerU VLM",
        "split_pages": args.split_pages,
        "digest_engine": args.digest_engine,
    }

    results: list[dict[str, Any]] = []
    effective_structure = bool(args.structure and args.digest_engine == "llm")
    for index, part in enumerate(parts, start=1):
        title = args.title
        if len(parts) > 1:
            title = f"{source_file.stem} part {index:03d}"
        cli_args = ["ingest", str(part), "--vault", str(vault)]
        if title:
            cli_args.extend(["--title", title])
        for tag in args.tag:
            cli_args.extend(["--tag", tag])
        completed = run_cli(project, cli_args, env=ingest_env(effective_structure, args.mineru_timeout, args.digest_engine))
        parsed = parse_key_value_stdout(completed.stdout)
        item = {"file": str(source_file), "part_file": str(part), "returncode": completed.returncode, **parsed}
        if completed.returncode != 0:
            item["status"] = "failed"
            report["errors"].append({"stage": "ingest", "file": str(part), "stderr": completed.stderr[-3000:]})
            report["status"] = "partial"
        else:
            source_id = parsed.get("source_id")
            item["status"] = parsed.get("status", "unknown")
            if source_id:
                report["updated_files"].append(str(vault / "derived" / source_id / "content.json"))
            if parsed.get("page"):
                report["generated_files"].append(parsed["page"])
                report["next_paths"].append(parsed["page"])
            if source_id and item["status"] == "parsed_only" and args.digest_engine == "codex":
                try:
                    maybe_prepare_digest_bundle(vault, source_id, report)
                    item["bundle"] = str(vault / "logs" / "codex-digest-bundles" / f"{source_id}.json")
                except Exception as exc:
                    report["errors"].append({"stage": "prepare-source", "source_id": source_id, "error": str(exc)})
                    report["status"] = "partial"
        results.append(item)
    report["results"]["files"] = results
    finish(report, vault)


def command_ingest_folder(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("ingest-folder", vars(args))
    project = project_path(args.project)
    cache = load_cache(vault)
    existing = set(cache.get("sources", {}).keys())
    files = sorted(path for path in Path(args.folder).glob("*") if path.is_file() and fnmatch.fnmatch(path.name, args.pattern))
    results: list[dict[str, Any]] = []
    effective_structure = bool(args.structure and args.digest_engine == "llm")

    for path in files:
        source_id = sha1_file(path)
        if args.skip_duplicates and source_id in existing:
            item = {"file": str(path), "source_id": source_id, "status": "skipped_duplicate"}
            results.append(item)
            report["skipped"].append(item)
            continue
        split_dir = vault / "logs" / "skill-runs" / f"{report['run_id']}-pdf-parts" / path.stem
        parts = split_pdf(path, split_dir, args.split_pages) if path.suffix.lower() == ".pdf" else [path]
        for index, part in enumerate(parts, start=1):
            title = None
            if len(parts) > 1:
                title = f"{path.stem} part {index:03d}"
            cli_args = ["ingest", str(part), "--vault", str(vault)]
            if title:
                cli_args.extend(["--title", title])
            for tag in args.tag:
                cli_args.extend(["--tag", tag])
            completed = run_cli(project, cli_args, env=ingest_env(effective_structure, args.mineru_timeout, args.digest_engine))
            parsed = parse_key_value_stdout(completed.stdout)
            item = {"file": str(path), "part_file": str(part), "returncode": completed.returncode, **parsed}
            if completed.returncode != 0:
                item["status"] = "failed"
                report["errors"].append({"stage": "ingest", "file": str(part), "stderr": completed.stderr[-3000:]})
                report["status"] = "partial"
            else:
                item_status = parsed.get("status", "unknown")
                item["status"] = item_status
                parsed_source_id = parsed.get("source_id")
                if parsed_source_id:
                    existing.add(parsed_source_id)
                    report["updated_files"].append(str(vault / "derived" / parsed_source_id / "content.json"))
                if parsed.get("page"):
                    report["generated_files"].append(parsed["page"])
                    report["next_paths"].append(parsed["page"])
                if item_status == "parsed_only" and parsed_source_id and args.digest_engine == "codex":
                    try:
                        maybe_prepare_digest_bundle(vault, parsed_source_id, report)
                        item["bundle"] = str(vault / "logs" / "codex-digest-bundles" / f"{parsed_source_id}.json")
                    except Exception as exc:
                        report["errors"].append({"stage": "prepare-source", "source_id": parsed_source_id, "error": str(exc)})
                        report["status"] = "partial"
            results.append(item)
    report["environment"] = {
        "project": str(project),
        "vault": str(vault),
        "pdf_parser": "MinerU VLM",
        "split_pages": args.split_pages,
        "digest_engine": args.digest_engine,
    }
    report["results"]["files"] = results
    finish(report, vault)


def command_structure_source(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("structure-source", vars(args))
    project = project_path(args.project)
    try:
        source_id = find_source_id(vault, args.source_id, args.source_page)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "lookup", "error": str(exc)})
        finish(report, vault)
        return

    if args.digest_engine == "codex":
        try:
            bundle_path, prompt_path, bundle = build_digest_bundle(vault, source_id)
        except Exception as exc:
            report["status"] = "failed"
            report["errors"].append({"stage": "prepare-source", "error": str(exc)})
            finish(report, vault)
            return
        report["results"] = {
            "source_id": source_id,
            "mode": "codex",
            "bundle_path": str(bundle_path),
            "prompt_path": str(prompt_path),
            "content_json_path": bundle["derived"]["content_json_path"],
            "content_markdown_path": bundle["derived"]["content_markdown_path"],
        }
        report["generated_files"].extend([str(bundle_path), str(prompt_path)])
        finish(report, vault)
        return

    completed = run_cli(project, ["structure-source", "--vault", str(vault), "--source-id", source_id])
    parsed = parse_key_value_stdout(completed.stdout)
    report["results"] = {"source_id": source_id, "cli_output": parsed, "mode": "llm"}
    if completed.returncode != 0:
        report["status"] = "failed"
        report["errors"].append({"stage": "structure", "source_id": source_id, "stderr": completed.stderr[-3000:], "stdout": completed.stdout[-3000:]})
    else:
        if parsed.get("page"):
            report["updated_files"].append(parsed["page"])
            report["next_paths"].append(parsed["page"])
        report["updated_files"].append(str(vault / "derived" / source_id / "digest.json"))
    finish(report, vault)


def command_prepare_source(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("prepare-source", vars(args))
    try:
        source_id = find_source_id(vault, args.source_id, None)
        bundle_path, prompt_path, bundle = build_digest_bundle(vault, source_id, args.output, args.prompt_output)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "prepare-source", "error": str(exc)})
        finish(report, vault)
        return
    report["results"] = {
        "source_id": source_id,
        "bundle_path": str(bundle_path),
        "prompt_path": str(prompt_path),
        "content_json_path": bundle["derived"]["content_json_path"],
        "content_markdown_path": bundle["derived"]["content_markdown_path"],
    }
    report["generated_files"].extend([str(bundle_path), str(prompt_path)])
    report["next_paths"].extend([str(bundle_path), str(prompt_path), str(vault / "derived" / source_id / "digest.json")])
    finish(report, vault)


def command_apply_digest(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("apply-digest", vars(args))
    cache = load_cache(vault)
    try:
        source_id = find_source_id(vault, args.source_id, None)
        source = ensure_source_record(vault, source_id, cache)
        payload = load_json(Path(args.digest_file).resolve(), {})
        digest = validate_digest_payload(payload, source_id)
        derived_markdown, derived_json = get_source_paths(vault, source_id, source)
        if not derived_json.exists():
            raise FileNotFoundError(f"Missing parsed JSON: {derived_json}")
        if not derived_markdown.exists():
            raise FileNotFoundError(f"Missing parsed Markdown: {derived_markdown}")

        digest_json = vault / "derived" / source_id / "digest.json"
        digest["derived_markdown_path"] = vault_relative(derived_markdown, vault)
        digest["derived_json_path"] = vault_relative(derived_json, vault)
        digest["digest_path"] = vault_relative(digest_json, vault)
        dump_json(digest_json, digest)

        title = digest["canonical_title"]
        page_path = source_page_path(vault, source_id, title, cache)
        source.update(
            {
                "source_id": source_id,
                "title": title,
                "status": "ready",
                "parse_status": "ready",
                "structured_status": "ready",
                "derived_markdown_path": vault_relative(derived_markdown, vault),
                "derived_json_path": vault_relative(derived_json, vault),
                "digest_path": vault_relative(digest_json, vault),
                "source_page": vault_relative(page_path, vault),
                "topics": digest["topics"],
                "entities": digest["entities"],
                "knowledge_type": digest["knowledge_type"],
                "source_language": digest["source_language"],
                "structured_at": digest["structured_at"],
            }
        )
        if "role_for_purpose" in digest:
            source["role_for_purpose"] = digest["role_for_purpose"]
        cache["sources"][source_id] = source
        write_text(page_path, render_source_page(vault, cache, source_id, title, digest))
        save_cache(vault, cache)
        rewrite_overview_page(vault, cache)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "apply-digest", "error": str(exc)})
        finish(report, vault)
        return
    report["results"] = {
        "source_id": source_id,
        "digest_path": str(digest_json),
        "source_page": str(page_path),
        "topics": digest["topics"],
        "entities": digest["entities"],
    }
    report["updated_files"].extend([str(digest_json), str(page_path), str(vault / ".wiki-cache.json"), str(vault / "wiki" / "overview.md")])
    report["next_paths"].append(str(page_path))
    finish(report, vault)


def command_prepare_topic(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("prepare-topic", vars(args))
    try:
        bundle_path, prompt_path, bundle = build_topic_bundle(vault, args.topic, args.output, args.prompt_output)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "prepare-topic", "error": str(exc)})
        finish(report, vault)
        return
    report["results"] = {
        "topic": args.topic,
        "bundle_path": str(bundle_path),
        "prompt_path": str(prompt_path),
        "supporting_sources": [row["source_id"] for row in bundle["supporting_sources"]],
    }
    report["generated_files"].extend([str(bundle_path), str(prompt_path)])
    finish(report, vault)


def command_apply_topic(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("apply-topic", vars(args))
    cache = load_cache(vault)
    try:
        payload = load_json(Path(args.digest_file).resolve(), {})
        digest = validate_topic_payload(payload, args.topic)
        digest_path = topic_digest_path(vault, args.topic)
        page_path = topic_page_path(vault, args.topic)
        dump_json(digest_path, digest)
        cache["topic_pages"][slugify(args.topic)] = {
            "topic": args.topic,
            "title": digest["title"],
            "digest_path": vault_relative(digest_path, vault),
            "page_path": vault_relative(page_path, vault),
            "source_ids": digest["source_ids"],
            "structured_at": digest["structured_at"],
        }
        write_text(page_path, render_topic_page(vault, cache, args.topic, digest))
        rewrite_source_pages(vault, cache, digest["source_ids"])
        save_cache(vault, cache)
        rewrite_overview_page(vault, cache)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "apply-topic", "error": str(exc)})
        finish(report, vault)
        return
    report["results"] = {
        "topic": args.topic,
        "digest_path": str(digest_path),
        "page_path": str(page_path),
        "source_ids": digest["source_ids"],
    }
    report["updated_files"].extend([str(digest_path), str(page_path), str(vault / ".wiki-cache.json"), str(vault / "wiki" / "overview.md")])
    finish(report, vault)


def command_prepare_entity(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("prepare-entity", vars(args))
    try:
        bundle_path, prompt_path, bundle = build_entity_bundle(vault, args.entity, args.output, args.prompt_output)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "prepare-entity", "error": str(exc)})
        finish(report, vault)
        return
    report["results"] = {
        "entity": args.entity,
        "bundle_path": str(bundle_path),
        "prompt_path": str(prompt_path),
        "supporting_sources": [row["source_id"] for row in bundle["supporting_sources"]],
    }
    report["generated_files"].extend([str(bundle_path), str(prompt_path)])
    finish(report, vault)


def command_apply_entity(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("apply-entity", vars(args))
    cache = load_cache(vault)
    try:
        payload = load_json(Path(args.digest_file).resolve(), {})
        digest = validate_entity_payload(payload, args.entity)
        digest_path = entity_digest_path(vault, args.entity)
        page_path = entity_page_path(vault, args.entity)
        dump_json(digest_path, digest)
        cache["entity_pages"][slugify(args.entity)] = {
            "entity": args.entity,
            "title": digest["title"],
            "digest_path": vault_relative(digest_path, vault),
            "page_path": vault_relative(page_path, vault),
            "source_ids": digest["source_ids"],
            "structured_at": digest["structured_at"],
        }
        write_text(page_path, render_entity_page(vault, cache, args.entity, digest))
        rewrite_source_pages(vault, cache, digest["source_ids"])
        save_cache(vault, cache)
        rewrite_overview_page(vault, cache)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"stage": "apply-entity", "error": str(exc)})
        finish(report, vault)
        return
    report["results"] = {
        "entity": args.entity,
        "digest_path": str(digest_path),
        "page_path": str(page_path),
        "source_ids": digest["source_ids"],
    }
    report["updated_files"].extend([str(digest_path), str(page_path), str(vault / ".wiki-cache.json"), str(vault / "wiki" / "overview.md")])
    finish(report, vault)


def command_audit_readiness(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("audit-readiness", vars(args))
    cache = load_cache(vault)
    pending: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source_id, source in sorted(cache.get("sources", {}).items()):
        if not isinstance(source, dict):
            continue
        seen.add(source_id)
        derived_markdown, derived_json = get_source_paths(vault, source_id, source)
        digest_path = vault / str(source.get("digest_path") or f"derived\\{source_id}\\digest.json")
        if derived_json.exists() and not digest_path.exists():
            pending.append(
                {
                    "source_id": source_id,
                    "title": source.get("title") or source_id,
                    "derived_json_path": str(derived_json),
                    "derived_markdown_path": str(derived_markdown),
                    "suggested_bundle": str(vault / "logs" / "codex-digest-bundles" / f"{source_id}.json"),
                }
            )

    for derived_json in sorted((vault / "derived").glob("*/content.json")):
        source_id = derived_json.parent.name
        if source_id in seen:
            continue
        digest_path = derived_json.parent / "digest.json"
        derived_markdown = derived_json.parent / "content.md"
        if digest_path.exists():
            continue
        pending.append(
            {
                "source_id": source_id,
                "title": source_id,
                "derived_json_path": str(derived_json),
                "derived_markdown_path": str(derived_markdown),
                "suggested_bundle": str(vault / "logs" / "codex-digest-bundles" / f"{source_id}.json"),
            }
        )

    report["results"] = {"pending_digest_count": len(pending), "pending_sources": pending}
    if pending:
        report["status"] = "partial"
        report["next_paths"].extend(item["suggested_bundle"] for item in pending)
    finish(report, vault)


def command_rebuild(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("rebuild", vars(args))
    project = project_path(args.project)
    completed = run_cli(project, ["rebuild", "--vault", str(vault)] + ([] if args.refresh_qmd else ["--no-refresh-qmd"]))
    parsed = parse_key_value_stdout(completed.stdout)
    report["results"] = parsed
    if completed.returncode != 0:
        report["status"] = "failed"
        report["errors"].append({"stage": "rebuild", "stderr": completed.stderr[-3000:], "stdout": completed.stdout[-3000:]})
    else:
        try:
            cache = load_cache(vault)
            report["results"]["rewritten_topic_pages"] = str(rewrite_index_pages(vault, cache, "topic"))
            report["results"]["rewritten_entity_pages"] = str(rewrite_index_pages(vault, cache, "entity"))
            report["results"]["pruned_legacy_topic_pages"] = str(prune_untracked_index_pages(vault, cache, "topic"))
            report["results"]["pruned_legacy_entity_pages"] = str(prune_untracked_index_pages(vault, cache, "entity"))
            report["results"]["rewritten_source_pages"] = str(rewrite_source_pages(vault, cache))
            overview_counts = rewrite_overview_page(vault, cache)
            report["results"]["overview_topics"] = str(overview_counts["topics"])
            report["results"]["overview_entities"] = str(overview_counts["entities"])
            save_cache(vault, cache)
        except Exception as exc:
            report["status"] = "partial"
            report["errors"].append({"stage": "page-rewrite", "error": str(exc)})
        report["updated_files"].extend(
            [
                str(vault / "wiki" / "overview.md"),
                str(vault / "wiki" / "topics"),
                str(vault / "wiki" / "entities"),
                str(vault / "wiki" / "sources"),
            ]
        )
        report["next_paths"].append(str(vault / "wiki" / "overview.md"))
    finish(report, vault)


def command_query(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("query", vars(args))
    project = project_path(args.project)
    completed = run_cli(project, ["query", args.question, "--vault", str(vault), "--limit", str(args.limit), "--json"])
    if completed.returncode != 0:
        report["status"] = "failed"
        report["errors"].append({"stage": "query", "stderr": completed.stderr[-3000:], "stdout": completed.stdout[-3000:]})
        finish(report, vault)
        return

    payload = json.loads(completed.stdout)
    for hit in payload.get("wiki_hits", []) + payload.get("source_hits", []):
        file_ref = str(hit.get("file", ""))
        match = re.search(r"/((?:wiki/)?(?:sources|topics|entities)/[^?]+\.md|wiki/overview\.md|overview\.md)(?:\?|$)", file_ref)
        if match:
            rel_path = match.group(1)
            if not rel_path.startswith("wiki/") and rel_path != "overview.md":
                rel_path = f"wiki/{rel_path}"
            if rel_path == "overview.md":
                rel_path = "wiki/overview.md"
            hit["knowledge_section"] = section_for_line(vault / rel_path.replace("/", os.sep), int(hit.get("line") or 1))
    report["results"] = payload
    finish(report, vault)


def audit_terms(values: list[str]) -> list[str]:
    low = {"and", "big", "china", "aggregate", "paper", "series", "working", "abstract", "introduction"}
    bad = []
    for value in values:
        lowered = str(value).lower()
        if lowered in low or re.fullmatch(r"\d+(\.\d+)*", lowered) or re.search(r"doi|cn\d{2,}|issn", lowered):
            bad.append(str(value))
    return bad


def command_audit_vault(args: argparse.Namespace) -> None:
    vault = Path(args.vault).resolve()
    report = base_report("audit-vault", vars(args))
    cache = load_cache(vault)

    unstructured = []
    missing = []
    noisy = []
    for source_id, item in cache.get("sources", {}).items():
        if not isinstance(item, dict):
            continue
        digest_path = str(item.get("digest_path") or "").strip()
        if not digest_path or not (vault / digest_path).exists():
            unstructured.append(source_id)
        for key in ["derived_markdown_path", "derived_json_path", "digest_path", "source_page"]:
            value = str(item.get(key) or "").strip()
            if not value:
                if key in {"digest_path", "source_page"}:
                    continue
                missing.append({"source_id": source_id, "field": key, "path": value})
                continue
            if not (vault / value).exists():
                missing.append({"source_id": source_id, "field": key, "path": value})
        bad_terms = audit_terms(list(item.get("topics") or []) + list(item.get("entities") or []))
        if bad_terms:
            noisy.append({"source_id": source_id, "terms": bad_terms})

    report["results"] = {
        "sources": len(cache.get("sources", {})),
        "topic_pages": len(cache.get("topic_pages", {})),
        "entity_pages": len(cache.get("entity_pages", {})),
        "unstructured_sources": unstructured,
        "missing_files": missing,
        "noisy_terms": noisy,
    }
    if unstructured or missing or noisy:
        report["status"] = "partial"
    finish(report, vault)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="General Knowledge Base skill task runner")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-vault")
    init.add_argument("--vault", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--language", default="zh")
    init.add_argument("--purpose", required=True)
    init.add_argument("--project")
    init.set_defaults(func=command_init_vault)

    thesis = sub.add_parser("init-thesis-workspace")
    thesis.add_argument("--vault", required=True)
    thesis.add_argument("--force", action=argparse.BooleanOptionalAction, default=False)
    thesis.set_defaults(func=command_init_thesis_workspace)

    ingest = sub.add_parser("ingest-file")
    ingest.add_argument("--file", required=True)
    ingest.add_argument("--vault", required=True)
    ingest.add_argument("--purpose", default="")
    ingest.add_argument("--project")
    ingest.add_argument("--tag", action="append", default=[])
    ingest.add_argument("--title")
    ingest.add_argument("--mineru-timeout", type=int)
    ingest.add_argument("--split-pages", type=int, default=50, help="Split PDFs into 50-page parts by default before sending each part to MinerU.")
    ingest.add_argument("--structure", action=argparse.BooleanOptionalAction, default=True)
    ingest.add_argument("--digest-engine", choices=["codex", "llm"], default="codex")
    ingest.set_defaults(func=command_ingest_file)

    folder = sub.add_parser("ingest-folder")
    folder.add_argument("--folder", required=True)
    folder.add_argument("--vault", required=True)
    folder.add_argument("--purpose", default="")
    folder.add_argument("--project")
    folder.add_argument("--pattern", default="*.pdf")
    folder.add_argument("--tag", action="append", default=[])
    folder.add_argument("--mineru-timeout", type=int)
    folder.add_argument("--split-pages", type=int, default=50, help="Split each PDF into 50-page parts by default before sending each part to MinerU.")
    folder.add_argument("--structure", action=argparse.BooleanOptionalAction, default=True)
    folder.add_argument("--skip-duplicates", action=argparse.BooleanOptionalAction, default=True)
    folder.add_argument("--digest-engine", choices=["codex", "llm"], default="codex")
    folder.set_defaults(func=command_ingest_folder)

    structure = sub.add_parser("structure-source")
    structure.add_argument("--vault", required=True)
    structure.add_argument("--source-id")
    structure.add_argument("--source-page")
    structure.add_argument("--project")
    structure.add_argument("--digest-engine", choices=["codex", "llm"], default="codex")
    structure.set_defaults(func=command_structure_source)

    prepare = sub.add_parser("prepare-source")
    prepare.add_argument("--vault", required=True)
    prepare.add_argument("--source-id", required=True)
    prepare.add_argument("--output")
    prepare.add_argument("--prompt-output")
    prepare.set_defaults(func=command_prepare_source)

    apply_digest = sub.add_parser("apply-digest")
    apply_digest.add_argument("--vault", required=True)
    apply_digest.add_argument("--source-id", required=True)
    apply_digest.add_argument("--digest-file", required=True)
    apply_digest.set_defaults(func=command_apply_digest)

    prepare_topic = sub.add_parser("prepare-topic")
    prepare_topic.add_argument("--vault", required=True)
    prepare_topic.add_argument("--topic", required=True)
    prepare_topic.add_argument("--output")
    prepare_topic.add_argument("--prompt-output")
    prepare_topic.set_defaults(func=command_prepare_topic)

    apply_topic = sub.add_parser("apply-topic")
    apply_topic.add_argument("--vault", required=True)
    apply_topic.add_argument("--topic", required=True)
    apply_topic.add_argument("--digest-file", required=True)
    apply_topic.set_defaults(func=command_apply_topic)

    prepare_entity = sub.add_parser("prepare-entity")
    prepare_entity.add_argument("--vault", required=True)
    prepare_entity.add_argument("--entity", required=True)
    prepare_entity.add_argument("--output")
    prepare_entity.add_argument("--prompt-output")
    prepare_entity.set_defaults(func=command_prepare_entity)

    apply_entity = sub.add_parser("apply-entity")
    apply_entity.add_argument("--vault", required=True)
    apply_entity.add_argument("--entity", required=True)
    apply_entity.add_argument("--digest-file", required=True)
    apply_entity.set_defaults(func=command_apply_entity)

    readiness = sub.add_parser("audit-readiness")
    readiness.add_argument("--vault", required=True)
    readiness.set_defaults(func=command_audit_readiness)

    rebuild = sub.add_parser("rebuild")
    rebuild.add_argument("--vault", required=True)
    rebuild.add_argument("--project")
    rebuild.add_argument("--refresh-qmd", action=argparse.BooleanOptionalAction, default=True)
    rebuild.set_defaults(func=command_rebuild)

    query = sub.add_parser("query")
    query.add_argument("--vault", required=True)
    query.add_argument("--question", required=True)
    query.add_argument("--limit", type=int, default=5)
    query.add_argument("--project")
    query.set_defaults(func=command_query)

    audit = sub.add_parser("audit-vault")
    audit.add_argument("--vault", required=True)
    audit.set_defaults(func=command_audit_vault)
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
