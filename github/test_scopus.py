"""Scopus 客户端冒烟测试。

用一个小 count 验证:
  1) API Key 能从 .env 读到
  2) 请求能成功返回
  3) 关键字段都拿得到
"""

from dotenv import load_dotenv

load_dotenv()

from clients.scopus import search, get_total

QUERY = 'TITLE-ABS-KEY("walkability") AND PUBYEAR > 2022'
COUNT = 5


def main() -> None:
    print(f"[Scopus 测试] query = {QUERY}")
    print(f"[Scopus 测试] count = {COUNT}\n")

    total = get_total(QUERY)
    print(f"命中总数: {total}")

    entries = search(QUERY, count=COUNT)
    print(f"实际返回: {len(entries)} 条\n")

    for i, e in enumerate(entries, 1):
        print(f"--- [{i}] ---")
        print("标题      :", (e.get("dc:title") or "")[:120])
        print("第一作者  :", e.get("dc:creator") or "")
        print("年份      :", (e.get("prism:coverDate") or "")[:4])
        print("期刊      :", e.get("prism:publicationName") or "")
        print("DOI       :", e.get("prism:doi") or "")
        print("被引数    :", e.get("citedby-count") or "")
        print("文献类型  :", e.get("subtypeDescription") or "")
        print("EID       :", e.get("eid") or "")
        print()


if __name__ == "__main__":
    main()
