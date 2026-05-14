"""Scopus Search API 客户端。

只暴露 search(),返回 Scopus 原始 entry 列表(不做字段重命名,交给上层处理)。
"""

import os
import time
import requests

SCOPUS_URL = "https://api.elsevier.com/content/search/scopus"
PAGE_SIZE = 25
MAX_RETRIES = 3
RETRY_SLEEP = 2.0
TIMEOUT = 30


def search(query: str, count: int = 50) -> list[dict]:
    """调用 Scopus Search API,自动分页累计到 count 篇。

    Args:
        query: Scopus 查询语法,例如 TITLE-ABS-KEY("walkability") AND PUBYEAR > 2022
        count: 最多返回多少篇(实际返回数可能更少,取决于命中总数)

    Returns:
        entry 列表,字段保持 Scopus 原始命名(dc:title / prism:doi 等)
    """
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 SCOPUS_API_KEY 未设置,请检查 .env 文件")

    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
    }

    entries: list[dict] = []
    start = 0
    total: int | None = None

    while len(entries) < count:
        remaining = count - len(entries)
        params = {
            "query": query,
            "count": min(PAGE_SIZE, remaining),
            "start": start,
        }
        data = _request_with_retry(SCOPUS_URL, headers, params)
        results = data.get("search-results", {})

        if total is None:
            total = int(results.get("opensearch:totalResults", 0) or 0)
            if total == 0:
                return []

        page = results.get("entry", []) or []
        # Scopus 在零结果时也可能返回单个 error entry
        if not page or (len(page) == 1 and "error" in page[0]):
            break

        entries.extend(page)
        start += len(page)

        if start >= total:
            break

    return entries[:count]


def get_total(query: str) -> int:
    """只取第一页拿命中总数,用于交互式预览("找到 X 篇")。"""
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 SCOPUS_API_KEY 未设置")
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    params = {"query": query, "count": 1, "start": 0}
    data = _request_with_retry(SCOPUS_URL, headers, params)
    return int(data.get("search-results", {}).get("opensearch:totalResults", 0) or 0)


def _request_with_retry(url: str, headers: dict, params: dict) -> dict:
    last_exc: Exception | None = None
    for _ in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
        except requests.RequestException as e:
            last_exc = e
            time.sleep(RETRY_SLEEP)
            continue

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            raise RuntimeError("Scopus API Key 无效(401)。请检查 .env 中的 SCOPUS_API_KEY。")
        if resp.status_code == 429:
            time.sleep(RETRY_SLEEP)
            continue

        msg = _extract_error_message(resp)
        raise RuntimeError(f"Scopus 请求失败: status={resp.status_code} message={msg}")

    if last_exc:
        raise RuntimeError(f"Scopus 网络异常,已重试 {MAX_RETRIES} 次: {last_exc}")
    raise RuntimeError(f"Scopus 持续返回 429,已重试 {MAX_RETRIES} 次")


def _extract_error_message(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return resp.text[:200]
    return (
        payload.get("service-error", {}).get("status", {}).get("statusText")
        or payload.get("error-response", {}).get("error-message")
        or payload.get("fault", {}).get("faultstring")
        or str(payload)[:200]
    )
