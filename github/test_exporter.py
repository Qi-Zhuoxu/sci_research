"""Exporter 冒烟测试 — 用 3 条假数据生成一个 xlsx 让用户肉眼检查布局/配色。

3 条记录分别覆盖 3 种摘要来源(Crossref / OpenAlex / 无),
方便核对颜色标注、卷期格式、链接超链接等细节。
"""

from exporter import export

DUMMY_RECORDS = [
    {
        "title": "Highly accurate protein structure prediction with AlphaFold",
        "first_author": "Jumper J.",
        "authors_full": "Jumper, John; Evans, Richard; Pritzel, Alexander; Green, Tim",
        "year": "2021",
        "journal": "Nature",
        "volume": "596",
        "issue": "7873",
        "doctype": "Article",
        "abstract": (
            "Proteins are essential to life, and understanding their structure "
            "can facilitate a mechanistic understanding of their function. "
            "Here we present AlphaFold, a neural-network-based model that "
            "achieves atomic-level accuracy in structure prediction... "
            "(此处省略,真实导出时会是完整长摘要,用于验证 wrap_text 自动换行)"
        ),
        "abstract_source": "Crossref",
        "keywords": "protein structure | deep learning | AlphaFold",
        "scopus_cited_by": "30000",
        "crossref_cited_by": 40982,
        "reference_count": 84,
        "doi": "10.1038/s41586-021-03819-2",
        "eid": "2-s2.0-85113840998",
    },
    {
        "title": "Adaptation and validation of the neighbourhood environment walkability scale for German-speaking youth (NEWS-Y-G)",
        "first_author": "Scheller D.A.",
        "authors_full": "Scheller, Daniel A.; Humpe, Andreas; Mess, Filip; Nogueira de Zorzi, Viviane",
        "year": "2026",
        "journal": "BMC Public Health",
        "volume": "26",
        "issue": "1",
        "doctype": "Article",
        "abstract": (
            "Adolescents' physical activity is related to characteristics of "
            "their neighbourhood environment. (OpenAlex 兜底的摘要,颜色应为浅紫)"
        ),
        "abstract_source": "OpenAlex",
        "keywords": "walkability | adolescents | NEWS-Y",
        "scopus_cited_by": "0",
        "crossref_cited_by": 0,
        "reference_count": 48,
        "doi": "10.1186/s12889-026-26590-3",
        "eid": "2-s2.0-105030884581",
    },
    {
        "title": "A paper that neither Crossref nor OpenAlex indexed",
        "first_author": "Doe J.",
        "authors_full": "Doe, John",
        "year": "2023",
        "journal": "Mystery Journal",
        "volume": "1",
        "issue": "",
        "doctype": "Article",
        "abstract": "",
        "abstract_source": "无",
        "keywords": "",
        "scopus_cited_by": "5",
        "crossref_cited_by": "",
        "reference_count": "",
        "doi": "10.0000/fake.2023",
        "eid": "2-s2.0-000000000000",
    },
]


def main() -> None:
    path = export(DUMMY_RECORDS, first_keyword="walkability test")
    print(f"已生成: {path}")
    print()
    print("请打开文件检查:")
    print("  [ ] 首行加粗灰底,且滚动时首行冻结")
    print("  [ ] 标题列宽约 60,摘要列宽约 80")
    print("  [ ] 第 1 行(AlphaFold)摘要长,验证自动换行")
    print("  [ ] 摘要来源列:第1行浅绿 / 第2行浅紫 / 第3行浅灰")
    print("  [ ] 第3行卷期显示为 '1'(没有 issue 不带括号)")
    print("  [ ] Scopus 链接和 DOI 链接是蓝色下划线,可点击")
    print("  [ ] 文件名形如 walkability_test_2026-05-14_xxxxxx.xlsx")


if __name__ == "__main__":
    main()
