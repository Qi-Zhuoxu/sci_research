"""OpenAlex 客户端冒烟测试。

重点验证倒排索引能正确还原成可读文本,以及它对 Crossref 漏掉的
摘要(例如昨天 BMC 那篇)是否真能兜上。
"""

from clients.openalex import fetch, restore_abstract

TEST_CASES = [
    ("10.1038/s41586-021-03819-2", "AlphaFold(对比 Crossref 摘要,看是否一致)"),
    ("10.1186/s12889-026-26590-3", "BMC 论文(Crossref 拿不到,验证 OpenAlex 能否兜上)"),
    ("10.9999/this-doi-does-not-exist-xyz", "伪造 DOI,应返回 None"),
]


def test_inverted_index_unit() -> None:
    """脱网单元测试:验证还原算法本身。"""
    print("\n========== 倒排索引还原单元测试 ==========")
    sample = {"the": [0, 3], "cat": [1], "sat": [2]}
    restored = restore_abstract(sample)
    print(f"输入: {sample}")
    print(f"输出: {restored!r}")
    assert restored == "the cat sat the", f"还原算法出错: {restored!r}"
    print("✓ 通过")


def main() -> None:
    test_inverted_index_unit()

    for doi, label in TEST_CASES:
        print(f"\n========== {label} ==========")
        print(f"DOI: {doi}")
        result = fetch(doi)
        if result is None:
            print("→ None (查不到或异常)")
            continue
        abstract = result["abstract"]
        print(f"摘要长度: {len(abstract)} 字符")
        if abstract:
            print(f"摘要预览: {abstract[:300]}...")
        else:
            print("摘要: (空,OpenAlex 也没有)")


if __name__ == "__main__":
    main()
