"""Crossref 客户端冒烟测试。

覆盖三种情况:
  1) 一个老牌已知 DOI,验证摘要/作者/卷期都能拿
  2) 一个昨天 Scopus 测试返回的真实 DOI,验证管道兼容
  3) 一个伪造 DOI,验证 None 处理
"""

from clients.crossref import fetch

TEST_CASES = [
    ("10.1038/s41586-021-03819-2", "AlphaFold 论文(Nature 2021,应有完整摘要)"),
    ("10.1186/s12889-026-26590-3", "Scopus 测试返回的 BMC Public Health DOI"),
    ("10.9999/this-doi-does-not-exist-xyz", "伪造 DOI,应返回 None"),
]


def main() -> None:
    for doi, label in TEST_CASES:
        print(f"\n========== {label} ==========")
        print(f"DOI: {doi}")
        result = fetch(doi)
        if result is None:
            print("→ None (查不到或异常)")
            continue
        print("标题      :", (result["title"] or "")[:120])
        print("作者      :", (result["authors"] or "")[:200])
        print("期刊      :", result["container_title"])
        print("卷/期/页  :", f"{result['volume']} / {result['issue']} / {result['page']}")
        print("参考文献数:", result["reference_count"])
        print("被引数    :", result["is_referenced_by_count"])
        abstract = result["abstract"]
        print(f"摘要长度  : {len(abstract)} 字符")
        if abstract:
            print(f"摘要预览  : {abstract[:250]}...")
        else:
            print("摘要      : (空,需要 OpenAlex 兜底)")


if __name__ == "__main__":
    main()
