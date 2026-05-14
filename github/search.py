"""学术论文检索工具 — 非交互式主入口。

两种配置方式(可叠加,CLI 覆盖 YAML):
  1. 读 query.yaml(默认)/ query.json / 任意 --config 指定的路径
  2. argparse 命令行参数

进度用普通 print,不用 tqdm(非终端环境会刷屏)。
跑完只打印 xlsx 路径,不自动 open。
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import yaml
from dotenv import load_dotenv

load_dotenv()

from clients import crossref, openalex, scopus
from exporter import export

VALID_FIELDS = {"TITLE", "ABS", "KEY", "TITLE-ABS-KEY", "ALL"}
VALID_DOCTYPES = {"ar", "re", "cp", "all"}
VALID_COMBINE = {"AND", "OR"}

DEFAULTS = {
    "field":       "TITLE-ABS-KEY",
    "year_start":  2015,
    "year_end":    datetime.now().year,
    "doc_type":    "ar",
    "max_results": 50,
    "combine":     "AND",
}
COUNT_MAX = 200
PROGRESS_EVERY = 10


# ---------- 配置加载 ---------- #

def load_config_file(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.strip():
        return {}
    if path.lower().endswith(".json"):
        return json.loads(text) or {}
    return yaml.safe_load(text) or {}


def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="学术论文检索工具 (Scopus + Crossref + OpenAlex)",
    )
    p.add_argument("--config", default="query.yaml",
                   help="配置文件路径(默认 query.yaml,也支持 .json)")
    p.add_argument("--keywords", help="逗号分隔的关键词")
    p.add_argument("--field", choices=sorted(VALID_FIELDS))
    p.add_argument("--year-start", type=int, dest="year_start")
    p.add_argument("--year-end", type=int, dest="year_end")
    p.add_argument("--doc-type", choices=sorted(VALID_DOCTYPES), dest="doc_type")
    p.add_argument("--max", type=int, dest="max_results",
                   help=f"最多返回篇数(上限 {COUNT_MAX})")
    p.add_argument("--combine", choices=sorted(VALID_COMBINE))
    return p.parse_args()


def resolve_config(args: argparse.Namespace) -> dict:
    cfg = load_config_file(args.config)

    kws_cli: list[str] | None = None
    if args.keywords:
        kws_cli = [k.strip() for k in args.keywords.split(",") if k.strip()]

    def pick(cli_val, key):
        if cli_val is not None:
            return cli_val
        if key in cfg and cfg[key] is not None:
            return cfg[key]
        return DEFAULTS.get(key)

    resolved = {
        "keywords":    kws_cli or cfg.get("keywords") or [],
        "field":       pick(args.field, "field"),
        "year_start":  pick(args.year_start, "year_start"),
        "year_end":    pick(args.year_end, "year_end"),
        "doc_type":    pick(args.doc_type, "doc_type"),
        "max_results": pick(args.max_results, "max_results"),
        "combine":     pick(args.combine, "combine"),
    }
    _validate(resolved, args.config)
    resolved["max_results"] = min(max(int(resolved["max_results"]), 1), COUNT_MAX)
    return resolved


def _validate(c: dict, config_path: str) -> None:
    errs: list[str] = []
    if not c["keywords"]:
        errs.append(
            f"未提供关键词。请在 {config_path} 写 keywords,或用 --keywords 'kw1,kw2'。"
        )
    if c["field"] not in VALID_FIELDS:
        errs.append(f"field 非法: {c['field']!r}(可选 {sorted(VALID_FIELDS)})")
    if c["doc_type"] not in VALID_DOCTYPES:
        errs.append(f"doc_type 非法: {c['doc_type']!r}(可选 {sorted(VALID_DOCTYPES)})")
    if c["combine"] not in VALID_COMBINE:
        errs.append(f"combine 非法: {c['combine']!r}(可选 AND / OR)")
    try:
        ys, ye = int(c["year_start"]), int(c["year_end"])
        if ys > ye:
            errs.append(f"year_start({ys}) 大于 year_end({ye})")
    except (TypeError, ValueError):
        errs.append("year_start / year_end 必须是整数")

    if errs:
        for e in errs:
            print(f"  ✗ {e}", file=sys.stderr)
        sys.exit(2)


# ---------- 检索式构造 ---------- #

def build_query(
    keywords: list[str],
    field: str,
    year_start: int,
    year_end: int,
    doc_type: str,
    combine: str,
) -> str:
    kw_expr = f" {combine} ".join(f'"{k}"' for k in keywords)
    parts = [f"{field}({kw_expr})"]
    parts.append(f"PUBYEAR > {int(year_start) - 1}")
    parts.append(f"PUBYEAR < {int(year_end) + 1}")
    if doc_type and doc_type.lower() != "all":
        parts.append(f'DOCTYPE("{doc_type}")')
    return " AND ".join(parts)


def pretty_query(q: str) -> str:
    q = q.replace(" AND PUBYEAR", "\n  AND PUBYEAR", 1)
    q = q.replace(" AND DOCTYPE", "\n  AND DOCTYPE")
    return "  " + q


# ---------- 三阶段管线 ---------- #

def run_crossref_phase(entries: list[dict]) -> dict[str, dict]:
    data: dict[str, dict] = {}
    success = 0
    total = len(entries)
    for i, e in enumerate(entries, 1):
        doi = e.get("prism:doi")
        if doi:
            meta = crossref.fetch(doi)
            if meta is not None:
                data[doi] = meta
                if meta.get("abstract"):
                    success += 1
        if i == total or i % PROGRESS_EVERY == 0:
            print(f"      {i}/{total}  累计有摘要 {success} 篇")
    return data


def run_openalex_phase(dois: list[str]) -> dict[str, str]:
    data: dict[str, str] = {}
    success = 0
    total = len(dois)
    if total == 0:
        print("      (无需兜底,Crossref 已全部覆盖)")
        return data
    for i, doi in enumerate(dois, 1):
        meta = openalex.fetch(doi)
        if meta is not None and meta.get("abstract"):
            data[doi] = meta["abstract"]
            success += 1
        if i == total or i % PROGRESS_EVERY == 0:
            print(f"      {i}/{total}  累计补上 {success} 篇")
    return data


# ---------- 合并 ---------- #

def merge_record(
    scopus_entry: dict,
    cr_meta: dict | None,
    openalex_abstract: str | None,
) -> dict:
    cr = cr_meta or {}
    cr_abs = cr.get("abstract") or ""

    if cr_abs:
        abstract, source = cr_abs, "Crossref"
    elif openalex_abstract:
        abstract, source = openalex_abstract, "OpenAlex"
    else:
        abstract, source = "", "无"

    first_author = scopus_entry.get("dc:creator") or ""
    return {
        "title":             (scopus_entry.get("dc:title") or "").strip(),
        "first_author":      first_author,
        "authors_full":      cr.get("authors") or first_author,
        "year":              (scopus_entry.get("prism:coverDate") or "")[:4],
        "journal":           scopus_entry.get("prism:publicationName") or "",
        "volume":            cr.get("volume") or "",
        "issue":             cr.get("issue") or "",
        "doctype":           scopus_entry.get("subtypeDescription") or "",
        "abstract":          abstract,
        "abstract_source":   source,
        "keywords":          scopus_entry.get("authkeywords") or "",
        "scopus_cited_by":   scopus_entry.get("citedby-count") or "",
        "crossref_cited_by": cr.get("is_referenced_by_count", "") if cr else "",
        "reference_count":   cr.get("reference_count", "") if cr else "",
        "doi":               scopus_entry.get("prism:doi") or "",
        "eid":               scopus_entry.get("eid") or "",
    }


# ---------- 主流程 ---------- #

def main() -> None:
    args = parse_cli()
    cfg = resolve_config(args)

    print("==== 学术论文检索工具 (Scopus + Crossref + OpenAlex) ====")
    print(f"配置来源: {args.config if os.path.exists(args.config) else '(默认值 + CLI)'}")
    print(f"关键词  : {cfg['keywords']}  (combine={cfg['combine']})")
    print(f"字段    : {cfg['field']}")
    print(f"年份    : {cfg['year_start']} - {cfg['year_end']}")
    print(f"类型    : {cfg['doc_type']}")
    print(f"上限    : {cfg['max_results']}")

    query = build_query(
        cfg["keywords"], cfg["field"],
        cfg["year_start"], cfg["year_end"],
        cfg["doc_type"], cfg["combine"],
    )

    print()
    print("Scopus 检索式:")
    print(pretty_query(query))
    print()

    t0 = time.time()

    print("[1/3] Scopus 检索中...")
    try:
        total_hits = scopus.get_total(query)
        entries = scopus.search(query, count=cfg["max_results"])
    except Exception as e:
        print(f"      错误: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"      找到 {total_hits} 篇,获取前 {len(entries)} 篇")

    if not entries:
        print("没有结果,程序退出。")
        return

    print(f"[2/3] Crossref 补摘要 ({len(entries)} 篇)...")
    crossref_data = run_crossref_phase(entries)

    dois_to_fill = [
        e["prism:doi"] for e in entries
        if e.get("prism:doi")
        and not (crossref_data.get(e["prism:doi"], {}).get("abstract"))
    ]
    print(f"[3/3] OpenAlex 兜底补摘要 ({len(dois_to_fill)} 篇)...")
    openalex_data = run_openalex_phase(dois_to_fill)

    records = [
        merge_record(
            e,
            crossref_data.get(e.get("prism:doi") or ""),
            openalex_data.get(e.get("prism:doi") or ""),
        )
        for e in entries
    ]

    elapsed = time.time() - t0
    n_total = len(records)
    n_cr = sum(1 for r in records if r["abstract_source"] == "Crossref")
    n_oa = sum(1 for r in records if r["abstract_source"] == "OpenAlex")
    n_with_abs = n_cr + n_oa

    print()
    print("完成统计:")
    print(f"  论文总数: {n_total}")
    print(f"  含摘要  : {n_with_abs} ({_pct(n_with_abs, n_total)})")
    print(f"    ├─ Crossref: {n_cr}")
    print(f"    └─ OpenAlex: {n_oa}")
    print(f"  无摘要  : {n_total - n_with_abs} ({_pct(n_total - n_with_abs, n_total)})")
    print(f"  耗时    : {elapsed:.1f} 秒")
    print()

    path = export(records, first_keyword=cfg["keywords"][0])
    print(f"结果已保存: {os.path.relpath(path)}")


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{round(n / total * 100)}%"


if __name__ == "__main__":
    main()
