"""
需求雷达 DemandRadar v2.0
监控 V2EX(RSS+DDG搜索) + 知乎 + GitHub + 闲鱼，发现真实付费需求
"""
import sys, time, hashlib, json, textwrap
from datetime import datetime, timedelta
from pathlib import Path

import re as _re
import feedparser
import requests
import sqlite_utils
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich import box

# ── paths ────────────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
DB     = BASE / "demands.db"
JARVES = "http://localhost:7860"

# ── keywords that signal a paying need ───────────────────────────────────────
PAY_KEYWORDS = [
    "求", "帮我", "有偿", "付费", "接单", "代做", "求助", "急", "悬赏",
    "爬虫", "自动化", "脚本", "数据处理", "excel", "报表", "采集", "批量",
    "定制", "开发", "外包", "多少钱", "怎么收费", "报价",
]
TECH_KEYWORDS = [
    "python", "excel", "自动化", "爬虫", "数据", "脚本", "api",
    "接口", "处理", "批量", "统计", "可视化", "报表",
]

# ── V2EX RSS feeds (tab/ URLs work; node/ URLs 404 as of 2026-05) ─────────────
V2EX_FEEDS = [
    ("all",  "https://www.v2ex.com/feed/tab/all.xml"),
    ("tech", "https://www.v2ex.com/feed/tab/tech.xml"),
    ("jobs", "https://www.v2ex.com/feed/tab/jobs.xml"),
]

# 强付费信号：必须含其中至少一个才进入AI评分
STRONG_PAY = ["有偿", "付费", "悬赏", "外包", "代做", "报价", "多少钱", "怎么收费", "接单", "求人帮做"]

console = Console()


# ── database ──────────────────────────────────────────────────────────────────
def get_db() -> sqlite_utils.Database:
    db = sqlite_utils.Database(DB)
    if "demands" not in db.table_names():
        db["demands"].create({
            "id":          str,
            "source":      str,
            "title":       str,
            "url":         str,
            "summary":     str,
            "score":       int,
            "price_hint":  str,
            "tags":        str,
            "found_at":    str,
            "notified":    int,
        }, pk="id")
    return db


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


# ── scoring (deterministic — gemma3-4b too unreliable for classification) ─────
def _estimate_price(combined: str) -> str:
    if "爬虫" in combined and any(k in combined for k in ["验证码", "登录", "反爬"]):
        return "800-2000元"
    if "爬虫" in combined:
        return "300-800元"
    if any(k in combined for k in ["excel", "报表", "数据清洗"]):
        return "200-600元"
    if any(k in combined for k in ["自动化", "批量", "脚本"]):
        return "200-600元"
    if any(k in combined for k in ["api", "接口", "对接"]):
        return "500-1500元"
    return "200-500元"


def score_with_jarves(title: str, summary: str) -> dict:
    combined = (title + " " + summary).lower()

    # hard disqualifiers
    disqualify = ["招聘", "求职", "跳槽", "面试", "内推", "薪资", "工资待遇",
                  "拼车", "开源社区", "远程职位", "合伙人招募", "全职招募",
                  "offer", "jd", "岗位描述", "依赖更新", "dependabot"]
    if any(k in combined for k in disqualify):
        return {"score": 0, "price": "N/A", "reason": "排除：招聘/依赖更新/求职"}

    # tier 1: explicit paid task (score 9)
    tier1_pay  = ["有偿", "付费求", "悬赏", "代做", "帮做"]
    tier1_tech = ["爬虫", "自动化脚本", "python脚本", "数据处理", "excel自动",
                  "批量处理", "数据采集", "自动填表", "定时任务"]
    if any(k in combined for k in tier1_pay) and any(k in combined for k in tier1_tech):
        return {"score": 9, "price": _estimate_price(combined), "reason": "明确付费+技术任务"}

    # tier 2: strong pay + tech (score 7)
    strong_pay = ["有偿", "付费", "悬赏", "代做", "外包定制", "多少钱",
                  "怎么收费", "接单", "找人帮做"]
    if any(k in combined for k in strong_pay) and any(k in combined for k in TECH_KEYWORDS):
        return {"score": 7, "price": _estimate_price(combined), "reason": "付费意向+技术需求"}

    # tier 3: soft pay + tech + price hint (score 6)
    soft_pay = ["帮我", "求助", "想请", "找人帮", "急需"]
    price_hint = any(k in combined for k in ["元", "块钱", "¥", "rmb", "rmb"])
    if any(k in combined for k in soft_pay) and any(k in combined for k in TECH_KEYWORDS):
        score = 6 if price_hint else 4
        return {"score": score, "price": _estimate_price(combined), "reason": "求助+技术需求"}

    return {"score": 1, "price": "未知", "reason": "弱相关"}


# ── fetchers ──────────────────────────────────────────────────────────────────
def fetch_v2ex(db: sqlite_utils.Database) -> int:
    new_count = 0
    for node, url in V2EX_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            console.print(f"[yellow]V2EX {node} 抓取失败: {e}[/]")
            continue
        for entry in feed.entries:
            uid   = make_id(entry.get("link", entry.get("title", "")))
            title = entry.get("title", "")
            link  = entry.get("link", "")
            summ  = entry.get("summary", "")[:500]

            if db["demands"].count_where("id = ?", [uid]):
                continue

            combined = (title + " " + summ).lower()
            # 预筛：至少要有付费词 OR 技术词（宽松入库）
            has_any = any(k in combined for k in PAY_KEYWORDS + TECH_KEYWORDS)
            if not has_any:
                continue

            scored = score_with_jarves(title, summ)
            if scored.get("score", 0) < 5:
                continue

            db["demands"].insert({
                "id":         uid,
                "source":     f"v2ex/{node}",
                "title":      title,
                "url":        link,
                "summary":    summ[:300],
                "score":      scored.get("score", 0),
                "price_hint": scored.get("price", "未知"),
                "tags":       node,
                "found_at":   datetime.now().isoformat(),
                "notified":   0,
            })
            new_count += 1
    return new_count


def fetch_v2ex_search(db: sqlite_utils.Database) -> int:
    """DuckDuckGo 搜索 V2EX 有偿帖 — 无需API key，无需登录"""
    try:
        from ddgs import DDGS
    except ImportError:
        console.print("[yellow]ddgs 未安装，跳过V2EX搜索[/]")
        return 0

    queries = [
        "site:v2ex.com 有偿 python",
        "site:v2ex.com 有偿 爬虫 脚本",
        "site:v2ex.com 有偿 自动化 数据",
        "site:v2ex.com 有偿 excel 处理",
    ]
    new_count = 0
    try:
        with DDGS() as d:
            for q in queries:
                try:
                    results = list(d.text(q, max_results=6))
                    for r in results:
                        href    = r.get("href", "")
                        title   = r.get("title", "")
                        snippet = r.get("body", "")[:300]
                        if "v2ex.com/t/" not in href:
                            continue

                        uid = make_id(href)
                        if db["demands"].count_where("id = ?", [uid]):
                            continue

                        scored = score_with_jarves(title, snippet)
                        if scored.get("score", 0) < 5:
                            continue

                        db["demands"].insert({
                            "id":         uid,
                            "source":     "v2ex/ddg",
                            "title":      title,
                            "url":        href,
                            "summary":    snippet,
                            "score":      scored.get("score", 0),
                            "price_hint": scored.get("price", "未知"),
                            "tags":       q,
                            "found_at":   datetime.now().isoformat(),
                            "notified":   0,
                        })
                        new_count += 1
                    time.sleep(1.5)
                except Exception as e:
                    console.print(f"[yellow]DDG '{q[:30]}' 失败: {e}[/]")
    except Exception as e:
        console.print(f"[yellow]DDG 初始化失败: {e}[/]")
    return new_count


def fetch_zhihu(db: sqlite_utils.Database) -> int:
    """知乎搜索 — 公开接口，无需登录"""
    keywords = ["python 自动化 求助", "excel 脚本 急", "数据爬取 帮忙"]
    new_count = 0
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    for kw in keywords:
        url = (
            "https://www.zhihu.com/api/v4/search_v3"
            f"?t=general&q={requests.utils.quote(kw)}&correction=1&offset=0&limit=10"
        )
        try:
            r = requests.get(url, headers=headers, timeout=15)
            data = r.json()
            for item in data.get("data", []):
                obj    = item.get("object", {})
                title  = obj.get("title") or obj.get("question", {}).get("title", "")
                link   = "https://www.zhihu.com/question/" + str(obj.get("id", ""))
                excerpt = obj.get("excerpt", "")[:300]

                if not title:
                    continue
                uid = make_id(link)
                if db["demands"].count_where("id = ?", [uid]):
                    continue

                scored = score_with_jarves(title, excerpt)
                if scored.get("score", 0) < 4:
                    continue

                db["demands"].insert({
                    "id":         uid,
                    "source":     "zhihu",
                    "title":      title,
                    "url":        link,
                    "summary":    excerpt,
                    "score":      scored.get("score", 0),
                    "price_hint": scored.get("price", "未知"),
                    "tags":       kw,
                    "found_at":   datetime.now().isoformat(),
                    "notified":   0,
                })
                new_count += 1
        except Exception as e:
            console.print(f"[yellow]知乎 '{kw}' 失败: {e}[/]")
    return new_count


def fetch_github(db: sqlite_utils.Database) -> int:
    """GitHub Issues 搜索 — 专找 bounty/paid 标签"""
    queries = [
        "bounty python is:open",
        "bounty automation is:open label:bounty",
        "paid script data processing is:open",
    ]
    headers = {"Accept": "application/vnd.github+json"}
    new_count = 0
    for q in queries:
        url = f"https://api.github.com/search/issues?q={requests.utils.quote(q)}&sort=created&per_page=10"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            items = r.json().get("items", [])
            for item in items:
                uid   = make_id(item["html_url"])
                title = item.get("title", "")
                body  = (item.get("body") or "")[:300]
                link  = item["html_url"]

                if db["demands"].count_where("id = ?", [uid]):
                    continue

                scored = score_with_jarves(title, body)
                if scored.get("score", 0) < 3:
                    continue

                db["demands"].insert({
                    "id":         uid,
                    "source":     "github",
                    "title":      title,
                    "url":        link,
                    "summary":    body,
                    "score":      scored.get("score", 0),
                    "price_hint": scored.get("price", "未知"),
                    "tags":       "github",
                    "found_at":   datetime.now().isoformat(),
                    "notified":   0,
                })
                new_count += 1
        except Exception as e:
            console.print(f"[yellow]GitHub '{q}' 失败: {e}[/]")
    return new_count


def fetch_xianyu(db: sqlite_utils.Database) -> int:
    """闲鱼搜索 — 抓公开搜索结果页，无需登录"""
    keywords = ["python脚本", "自动化脚本", "爬虫定制", "excel自动化", "数据处理"]
    new_count = 0
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.0 Mobile/15E148 Safari/604.1",
        "Referer": "https://www.goofish.com/",
    }
    for kw in keywords:
        url = f"https://www.goofish.com/search?q={requests.utils.quote(kw)}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            # 闲鱼商品卡片 — 标题在 .item-title 或 [data-item]
            items = soup.select(".item-title") or soup.select("[class*='title']")
            for item in items[:10]:
                title = item.get_text(strip=True)
                if not title or len(title) < 4:
                    continue
                # 闲鱼无固定商品链接，用标题+关键词生成唯一ID
                uid   = make_id(kw + title)
                link  = f"https://www.goofish.com/search?q={requests.utils.quote(kw)}"

                if db["demands"].count_where("id = ?", [uid]):
                    continue

                combined = title.lower()
                has_tech = any(k in combined for k in TECH_KEYWORDS)
                if not has_tech:
                    continue

                scored = score_with_jarves(title, kw)
                if scored.get("score", 0) < 4:
                    continue

                db["demands"].insert({
                    "id":         uid,
                    "source":     "xianyu",
                    "title":      title,
                    "url":        link,
                    "summary":    f"关键词搜索: {kw}",
                    "score":      scored.get("score", 0),
                    "price_hint": scored.get("price", "未知"),
                    "tags":       kw,
                    "found_at":   datetime.now().isoformat(),
                    "notified":   0,
                })
                new_count += 1
        except Exception as e:
            console.print(f"[yellow]闲鱼 '{kw}' 失败: {e}[/]")
    return new_count


# ── display ───────────────────────────────────────────────────────────────────
def show_digest(db: sqlite_utils.Database, hours: int = 24):
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    rows   = list(db["demands"].rows_where(
        "found_at > ? ORDER BY score DESC LIMIT 30", [cutoff]
    ))

    console.print(f"\n[bold cyan]需求雷达 DemandRadar — 过去{hours}h 摘要[/]")
    console.print(f"共 [bold]{len(rows)}[/] 条机会\n")

    if not rows:
        console.print("[dim]暂无高分需求[/]")
        return

    table = Table(box=box.ROUNDED, show_lines=True, expand=True)
    table.add_column("分", style="bold yellow", width=4)
    table.add_column("来源", width=10)
    table.add_column("标题", min_width=30)
    table.add_column("估价", width=14)
    table.add_column("链接", style="dim", min_width=30)

    for row in rows:
        table.add_row(
            str(row["score"]),
            row["source"],
            textwrap.shorten(row["title"], 50),
            row["price_hint"],
            row["url"][:60],
        )
    console.print(table)


# ── main ──────────────────────────────────────────────────────────────────────
def run_once():
    db = get_db()
    console.print(f"[bold green][{datetime.now().strftime('%H:%M:%S')}] 开始抓取...[/]")
    n1 = fetch_v2ex(db)
    n1b = fetch_v2ex_search(db)
    console.print(f"  V2EX: +{n1} (RSS) +{n1b} (搜索)")
    n2 = fetch_zhihu(db)
    console.print(f"  知乎: +{n2}")
    n3 = fetch_github(db)
    console.print(f"  GitHub: +{n3}")
    n4 = fetch_xianyu(db)
    console.print(f"  闲鱼: +{n4}")
    total = db["demands"].count
    console.print(f"  数据库共 {total} 条记录")
    return n1 + n1b + n2 + n3 + n4


def run_daemon(interval_min: int = 30):
    """持续监控模式"""
    console.print(f"[bold]需求雷达启动，每 {interval_min} 分钟抓一次[/]  Ctrl-C 退出\n")
    while True:
        run_once()
        show_digest(get_db(), hours=24)
        console.print(f"\n[dim]下次抓取: {interval_min} 分钟后...[/]\n")
        time.sleep(interval_min * 60)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="需求雷达 DemandRadar")
    p.add_argument("--once",   action="store_true", help="抓一次就退出")
    p.add_argument("--digest", action="store_true", help="只看摘要")
    p.add_argument("--hours",  type=int, default=24, help="摘要时间窗口(小时)")
    p.add_argument("--interval", type=int, default=30, help="守护模式间隔(分钟)")
    args = p.parse_args()

    if args.digest:
        show_digest(get_db(), hours=args.hours)
    elif args.once:
        run_once()
        show_digest(get_db(), hours=args.hours)
    else:
        run_daemon(interval_min=args.interval)
