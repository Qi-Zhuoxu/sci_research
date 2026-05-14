"""Crossref REST API 客户端。

用 DOI 拉作者全名单、摘要、卷期、引用计数。Crossref 无需 Key,
但要带礼貌 User-Agent;摘要常带 JATS 标签,需要剥离。
"""

import html
import re
import time
import requests

CROSSREF_URL = "https://api.crossref.org/works/{doi}"
USER_AGENT = "sci-research-tool/1.0 (mailto:placeholder@example.com)"
RATE_LIMIT_SLEEP = 0.1
TIMEOUT = 30

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def fetch(doi: str) -> dict | None:
    """用 DOI 拉 Crossref 元数据,返回标准化字典;查不到或异常返回 None。

    返回字段(全部 snake_case,空值用空串/0):
      title, authors, abstract, container_title,
      volume, issue, page,
      reference_count, is_referenced_by_count
    """
    if not doi:
        return None

    time.sleep(RATE_LIMIT_SLEEP)
    url = CROSSREF_URL.format(doi=doi.strip())
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        # 404 = DOI 不在 Crossref;其他错误也静默跳过,不让单条挂掉整批
        return None

    try:
        msg = resp.json().get("message") or {}
    except ValueError:
        return None

    return _normalize(msg)


def clean_abstract(jats_html: str) -> str:
    """剥离 <jats:*> / <p> 等标签,解码 HTML 实体,合并空白。"""
    if not jats_html:
        return ""
    text = _TAG_RE.sub(" ", jats_html)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _normalize(msg: dict) -> dict:
    title_list = msg.get("title") or []
    container_list = msg.get("container-title") or []

    return {
        "title": title_list[0] if title_list else "",
        "authors": _format_authors(msg.get("author") or []),
        "abstract": clean_abstract(msg.get("abstract", "")),
        "container_title": container_list[0] if container_list else "",
        "volume": msg.get("volume") or "",
        "issue": msg.get("issue") or "",
        "page": msg.get("page") or "",
        "reference_count": int(msg.get("reference-count") or 0),
        "is_referenced_by_count": int(msg.get("is-referenced-by-count") or 0),
    }


def _format_authors(authors: list[dict]) -> str:
    parts: list[str] = []
    for a in authors:
        if not isinstance(a, dict):
            continue
        if a.get("family"):
            family = str(a["family"]).strip()
            given = str(a.get("given") or "").strip()
            parts.append(f"{family}, {given}" if given else family)
        elif a.get("name"):
            # 机构作者
            parts.append(str(a["name"]).strip())
    return "; ".join(parts)
