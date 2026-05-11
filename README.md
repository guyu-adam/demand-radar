# demand-radar

**实时监控 V2EX、知乎、GitHub、闲鱼上的付费技术需求，帮你第一时间找到真实外包订单。无需 AI API，纯确定性评分。**

**Real-time monitor for paid tech task requests on V2EX, Zhihu, GitHub, and Xianyu. Find real freelance orders before anyone else. No AI API required — pure deterministic scoring.**

---

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![No API Key](https://img.shields.io/badge/API%20key-none%20required-brightgreen.svg)](demand_radar.py)
[![Sources: 4](https://img.shields.io/badge/sources-4%20platforms-orange.svg)](demand_radar.py)
[![DB: SQLite](https://img.shields.io/badge/storage-SQLite-lightgrey.svg)](demand_radar.py)

---

## 解决什么问题 / The Problem

技术人想接外包，但需求散落在各个平台，手动刷帖效率极低。demand-radar 7×24 自动抓取，按付费意愿和技术匹配度打分排序，每次只看高分帖。

Tech freelancers waste hours manually browsing platforms for paid work. demand-radar crawls 4 platforms continuously, scores every post by pay intent and tech relevance, and surfaces only the high-value ones.

---

## 监控平台 / Monitored Sources

| 平台 / Platform | 抓取方式 / Method | 更新频率 / Frequency |
|---|---|---|
| **V2EX** | RSS + DuckDuckGo 搜索 | 每轮每次 |
| **知乎** | 公开搜索接口 | 每轮每次 |
| **GitHub Issues** | GitHub Search API | 每轮每次（`is:bounty` / `is:paid` 标签） |
| **闲鱼** | 公开搜索结果页 | 每轮每次 |

---

## 评分逻辑 / Scoring

每篇帖子从两个维度打分（满分各 5 分，合计 10 分）：

Each post is scored on two dimensions (max 5 each, total 10):

**付费意愿 / Pay intent keywords**
```
有偿, 付费, 悬赏, 求外包, 有报酬, bounty, paid, hire, contract, freelance...
```

**技术匹配 / Tech stack keywords**
```
Python, 爬虫, 数据分析, 自动化, API, 量化, AI, 机器学习, Node.js, Docker...
```

只展示合计分数 ≥ 3 的帖子，避免噪音。  
Only posts with total score ≥ 3 are shown, filtering noise.

---

## 实测输出 / Live Output Sample

```
┌─────────────────────────────────────────────────────────────────────┐
│  demand-radar  ·  2026-05-12 06:50  ·  扫描 4 平台 / 4 platforms    │
├──────┬─────────┬──────────────────────────────────────────┬─────────┤
│ 分数 │ 平台    │ 标题                                      │ 时间    │
├──────┼─────────┼──────────────────────────────────────────┼─────────┤
│  8/10│ V2EX   │ [有偿] 求 Python 爬虫帮忙抓某网站数据      │ 10m ago │
│  7/10│ GitHub │ [Bounty $200] Add async support to SDK    │ 23m ago │
│  7/10│ 知乎   │ 有偿求助：量化策略回测代码优化             │ 1h ago  │
│  6/10│ 闲鱼   │ 招 Python 自动化脚本开发，500元           │ 2h ago  │
│  6/10│ V2EX   │ 求外包：微信小程序 + 后端 API 开发        │ 3h ago  │
└──────┴─────────┴──────────────────────────────────────────┴─────────┘
本轮新增 5 条  ·  数据库共 128 条  ·  下次扫描 15min 后
```

---

## 快速开始 / Quick Start

```bash
git clone https://github.com/guyu-adam/demand-radar.git
cd demand-radar
pip install -r requirements.txt

# 单次扫描 / Single scan
python demand_radar.py --once

# 持续监控（默认 15min 间隔）/ Continuous monitor (default 15min)
python demand_radar.py

# 后台运行 / Background daemon
bash run.sh
```

---

## 配置 / Configuration

在 `demand_radar.py` 顶部修改关键词：

```python
PAY_KEYWORDS = ["有偿", "付费", "悬赏", "bounty", "paid", "hire", ...]
TECH_KEYWORDS = ["Python", "爬虫", "数据分析", "自动化", "API", ...]
SCAN_INTERVAL = 900   # 秒 / seconds between scans
MIN_SCORE     = 3     # 最低展示分数 / minimum display score
```

---

## 数据存储 / Storage

所有抓到的帖子存入本地 SQLite（`demand_radar.db`），字段包括：

```
id · platform · title · url · score_pay · score_tech · score_total · created_at · seen
```

可用 `sqlite-utils` 或任意 SQL 工具查询历史。

---

## 为什么不用 AI API / Why No AI

- 延迟更低：确定性打分 < 5ms，API 调用需要 500ms+
- 无成本：不烧 OpenAI / Claude token
- 离线运行：断网也能用
- 可解释：每个分数都能追溯到具体关键词命中

Deterministic scoring is faster (<5ms vs 500ms+ for API), free, offline-capable, and fully explainable.

---

## 配合 Miser 使用 / Works Great with Miser

如果你用 Claude Code，可以用 [Miser](https://github.com/guyu-adam/miser) 把 demand-radar 的输出摘要交给本地 LLM 做进一步筛选，不花 API token。

Pair with [Miser](https://github.com/guyu-adam/miser) to let a local LLM further filter results without spending API tokens.

---

## License

MIT
