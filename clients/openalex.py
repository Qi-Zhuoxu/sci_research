"""OpenAlex API 客户端(摘要兜底)。

只补 Crossref 拿不到的摘要。OpenAlex 把摘要存成倒排索引
(单词→位置数组),需要还原成正常句子。
"""

import time
import requests

OPENALEX_URL = "https://api.openalex.org/works/doi:{doi}"
USER_AGENT = "sci-research-tool/1.0 (mailto:placeholder@example.com)"
RATE_LIMIT_SLEEP = 0.1
TIMEOUT = 30


def fetch(doi: str) -> dict | None:
    """用 DOI 拉 OpenAlex 记录,返回 {'abstract': str};查不到或异常返回 None。"""
    if not doi:
        return None

    time.sleep(RATE_LIMIT_SLEEP)
    url = OPENALEX_URL.format(doi=doi.strip())
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    return {
        "abstract": restore_abstract(data.get("abstract_inverted_index") or {}),
    }


def restore_abstract(inverted_index: dict) -> str:
    """把 {word: [pos, pos, ...]} 还原成按位置排列的正常文本。"""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, locs in inverted_index.items():
        if not isinstance(locs, list):
            continue
        for pos in locs:
            if isinstance(pos, int):
                positions.append((pos, word))
    if not positions:
        return ""
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)
