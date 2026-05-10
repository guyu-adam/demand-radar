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

## Output

```
需求雷达 — 过去24h 摘要   5 条机会

╭──────┬────────────┬────────────────────────────────────┬──────────────╮
│ 分   │ 来源       │ 标题                                │ 估价         │
├──────┼────────────┼────────────────────────────────────┼──────────────┤
│  9   │ v2ex/ddg   │ 有偿求助：Excel数据清洗+自动报表    │ 200-600元    │
│  7   │ v2ex/all   │ 求 Python 爬虫帮我抓某网站数据      │ 300-800元    │
╰──────┴────────────┴────────────────────────────────────┴──────────────╯
```

Results are stored in `demands.db` (SQLite). Deduplication by URL hash.

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
