# sci-research

学术论文检索工具 — Scopus 检索发现,Crossref + OpenAlex 补全摘要,导出 Excel。

不依赖机构订阅,只用三个公开 API(Scopus 需要免费注册的开发者 Key)。
全程可在 Claude Code 内驱动:编辑 `query.yaml` → 跑 `python search.py` → 读结果 xlsx。

---

## 架构

```
Scopus Search API   → 检索发现(标题/作者/年份/期刊/DOI/被引/EID)
       ↓ DOI
Crossref REST API   → 补全完整作者列表 + 摘要(若有)+ 卷期 + 引用计数
       ↓ 仍缺摘要
OpenAlex API        → 用 DOI 兜底补摘要(摘要覆盖率更高)
       ↓
合并 → 导出 results/{slug}_{timestamp}.xlsx
```

---

## 快速开始

```bash
# 1. 克隆并装依赖
git clone https://github.com/<your-username>/sci-research.git
cd sci-research
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 用编辑器把 .env 里的 your_key_here 换成你真实的 Scopus API Key
# 申请地址:https://dev.elsevier.com/apikey/manage  (免费,注册即送)

# 3. 编辑 query.yaml(已带示例)

# 4. 跑
python search.py
```

跑完终端会打印 xlsx 路径,例如 `results/walkability_2026-05-14_143022.xlsx`。

**云端运行(GitHub Codespaces / Claude Code Web 等)**:不要把 `.env` 提交到仓库。
改用平台的 Secrets 功能注入环境变量:
- GitHub Actions / Codespaces:在仓库 Settings → Secrets and variables 添加 `SCOPUS_API_KEY`
- 任意 Linux shell:`export SCOPUS_API_KEY=xxx` 后再跑 `python search.py`

---

## 配置:`query.yaml`

| 字段 | 类型 | 默认 | 取值 / 说明 |
|---|---|---|---|
| `keywords` | list[str] | (必填) | 关键词列表,每项独立带引号 |
| `combine` | str | `AND` | `AND`(都包含)/ `OR`(任一) |
| `field` | str | `TITLE-ABS-KEY` | `TITLE` / `ABS` / `KEY` / `TITLE-ABS-KEY` / `ALL` |
| `year_start` | int | `2015` | 起始年份(含) |
| `year_end` | int | 当前年 | 结束年份(含) |
| `doc_type` | str | `ar` | `ar`=Article / `re`=Review / `cp`=会议论文 / `all`=不限 |
| `max_results` | int | `50` | 1-200 |

示例:

```yaml
keywords:
  - "15-minute city"
  - "walkability"
combine: AND
field: TITLE-ABS-KEY
year_start: 2020
year_end: 2024
doc_type: ar
max_results: 50
```

构造出的 Scopus 检索式:

```
TITLE-ABS-KEY("15-minute city" AND "walkability")
AND PUBYEAR > 2019 AND PUBYEAR < 2025
AND DOCTYPE("ar")
```

---

## 命令行参数(可选,覆盖 yaml)

```bash
# 临时换关键词,其他字段沿用 yaml
python search.py --keywords "transit-oriented development, gentrification"

# 临时换年份和上限
python search.py --year-start 2018 --year-end 2024 --max 100

# 用另一份配置
python search.py --config experiments/tod_review.yaml
```

完整参数:`--keywords`(逗号分隔)、`--field`、`--year-start`、`--year-end`、
`--doc-type`、`--max`、`--combine`、`--config`。

---

## 输出 Excel 列说明

| 列 | 数据来源(按优先级) |
|---|---|
| 序号 | 自增 |
| 标题 | Scopus |
| 第一作者 | Scopus |
| 全部作者 | Crossref → Scopus 第一作者兜底 |
| 年份 / 期刊 / 文献类型 | Scopus |
| 卷期 | Crossref(格式 `Vol(Issue)`) |
| 摘要 | Crossref → OpenAlex → 空 |
| **摘要来源** | `Crossref`(浅绿) / `OpenAlex`(浅紫) / `无`(浅灰) |
| 关键词 | Scopus `authkeywords` |
| Scopus 被引数 | Scopus `citedby-count` |
| Crossref 被引数 | Crossref `is-referenced-by-count` |
| 参考文献数 | Crossref `reference-count` |
| DOI / Scopus 链接 / DOI 链接 | 由 DOI 和 EID 拼接 |

样式:首行加粗灰底冻结、标题列宽 60、摘要列宽 80 自动换行、链接列为蓝色超链接。

---

## API 限制与摘要覆盖率

### 配额

| API | 鉴权 | 速率 | 配额(典型) |
|---|---|---|---|
| **Scopus** | API Key(免费,X-ELS-APIKey header) | 自动分页每页 25 | 每周约 20,000 次请求 |
| **Crossref** | 无,礼貌池靠 User-Agent + mailto | 客户端加 0.1s 间隔 | 实测约 50 req/s 上限 |
| **OpenAlex** | 无,礼貌池靠 mailto | 客户端加 0.1s 间隔 | 较宽松,生产建议 < 10 req/s |

工具已经内置:Scopus 401/429 重试、Crossref/OpenAlex 单条失败不阻塞批次、所有客户端礼貌 sleep。

### 摘要覆盖率预期

覆盖率高度依赖**年份**和**学科**,实测大致:

| 年份范围 | 典型覆盖率 | 说明 |
|---|---|---|
| 2015-2022 | 85-95% | 出版社元数据已稳定回填 |
| 2023-2024 | 70-85% | 主流期刊覆盖好,小众期刊有缺漏 |
| 2025 当年 | 40-60% | 部分新刊还在 Crossref 排队 |
| 当年新刊 | 30-50% | 很多论文 DOI 已发但摘要未推 |

如果跑出来覆盖率明显偏低,通常是因为 Scopus 默认按时间排序、前 N 篇全是当年最新刊。
解决办法:**把 year_end 往前缩一年**,或在 yaml 里增加 `year_start` 范围。

### 无摘要怎么办

落进 `无` 那一类的论文,可以手动:
- 通过 DOI 链接(xlsx 里现成的)跳到出版社页面
- 通过 Scopus 链接打开 Scopus 网页版查看(需要订阅)
- 在 Google Scholar 搜标题,通常能找到 preprint 或开放访问版本

---

## 项目结构

```
sci-research/
├── .env                  # SCOPUS_API_KEY=...  (git 忽略)
├── .gitignore
├── requirements.txt
├── query.yaml            # 默认配置
├── search.py             # 主入口
├── exporter.py           # Excel 导出
├── clients/
│   ├── __init__.py
│   ├── scopus.py
│   ├── crossref.py
│   └── openalex.py
├── test_scopus.py        # 各客户端冒烟测试
├── test_crossref.py
├── test_openalex.py
├── test_exporter.py
├── results/              # 输出目录(git 忽略)
└── README.md
```

---

## 安全约定

- `.env` 在 `.gitignore` 里,**永远不要 commit**
- 代码中只通过 `os.getenv("SCOPUS_API_KEY")` 读取,无任何硬编码
- Crossref / OpenAlex 的 User-Agent 里的 `mailto:` 用的是占位字符串,
  正式发表用建议改成真实邮箱,可以进礼貌池获得更高速率

---

## 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| `Scopus API Key 无效(401)` | 检查 `.env` 里 key 是否正确;免费 key 通常机构外网络也可用 |
| `找到 0 篇` | 检查 yaml 里 keywords 拼写;`combine: AND` 配两个不相关词会零命中,试 `OR` |
| Crossref 全 0 成功 | 大概率被速率限制了;`crossref.py` 的 `RATE_LIMIT_SLEEP` 调大到 0.3 |
| OpenAlex 摘要乱序 | 倒排索引位置有重复词;算法已按位置排序,但若仍异常,把对应 DOI 贴出来排查 |
| 覆盖率持续 < 30% | 看终端打印的所有论文是不是同一年。把 `year_end` 提前 1 年试试 |

---

## 各模块单独冒烟测试

```bash
python test_scopus.py     # 验 Scopus Key + 取 5 篇示例
python test_crossref.py   # 验 Crossref 三个用例
python test_openalex.py   # 验 OpenAlex + 倒排索引还原算法
python test_exporter.py   # 生成一个含全 3 种摘要来源的 xlsx 看样式
```
