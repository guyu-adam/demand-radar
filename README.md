# demand-radar

Monitor V2EX (RSS + DuckDuckGo search) and GitHub for real paid tech task requests — freelancers, automation work, data processing, scraping.

No AI API required. Pure deterministic keyword scoring.

---

## What it does

Traditional business owners post "paid help wanted" requests on V2EX and similar sites — Excel automation, web scrapers, data processing scripts. They have budgets but don't know where to find developers.

This tool monitors those sources continuously and surfaces the ones worth responding to.

---

## Quick start

```bash
pip install feedparser requests rich sqlite-utils beautifulsoup4 duckduckgo-search

# Run once
python demand_radar.py --once

# Show digest of last 24h (no network)
python demand_radar.py --digest

# Daemon mode (fetch every 30 min)
python demand_radar.py --interval 30

# Or use the included script
bash run.sh
```

---

## Demo

```
$ python demand_radar.py --once
[V2EX/RSS]  fetching 3 feeds...  47 posts
[V2EX/DDG]  searching with pay keywords...  12 results
[GitHub]    searching issues...  3 results
[filter]    62 total → 8 pass keyword gate → 4 score ≥ 7

$ python demand_radar.py --digest

需求雷达 — 过去24h 摘要   4 条机会
┏━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ 分   ┃ 来源       ┃ 标题                                     ┃ 估价         ┃
┡━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  9   │ v2ex/ddg   │ 有偿 Excel多表汇总+自动生成月报           │ 200-600元    │
│  9   │ v2ex/jobs  │ 付费求 Python 爬取某招聘网简历数据        │ 300-800元    │
│  7   │ v2ex/all   │ 求大佬帮写脚本批量处理图片重命名          │ 200-500元    │
│  7   │ github     │ [Bounty $50] add CSV export to dashboard  │ ~350元       │
└──────┴────────────┴──────────────────────────────────────────┴──────────────┘
```

Results are stored in `demands.db` (SQLite). Deduplication by URL hash.

---

## How scoring works

No LLM required. Deterministic keyword tiers:

| Score | Signal |
|-------|--------|
| 9 | Strong pay word (有偿/付费/悬赏) + specific tech task |
| 7 | Strong pay signal + any tech keyword |
| 5–6 | Soft pay signal + tech + price hint |
| <5 | Filtered out |

Disqualifiers: job listings, résumés, dependency-update bots.

---

## Sources

- **V2EX RSS** — `tab/all`, `tab/tech`, `tab/jobs` feeds
- **V2EX DuckDuckGo search** — site:v2ex.com with pay keywords (catches posts not in RSS window)
- **GitHub Issues** — searches for paid bounty issues in key repos

---

## Configuration

Edit the constants at the top of `demand_radar.py`:

```python
JARVES = "http://localhost:7860"  # optional local LLM endpoint (unused by default)
V2EX_FEEDS = [...]                # RSS feeds to monitor
PAY_KEYWORDS = [...]              # keywords triggering fetch
STRONG_PAY = [...]                # high-confidence pay signals
```

---

## Requirements

- Python 3.9+
- `feedparser requests rich sqlite-utils beautifulsoup4 duckduckgo-search`

---

## License

MIT
