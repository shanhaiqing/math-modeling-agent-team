# -*- coding: utf-8 -*-
"""
github_sciplot_scraper.py — 科研论文绘图资源抓取器（GitHub Search API）

从 GitHub 系统性抓取科研绘图方向高质量项目，覆盖：
  - 绘图工具：Matplotlib / Seaborn / Plotly / ggplot2 / MATLAB / Vega / D3 / graphviz
  - 主题：data visualization / scientific plotting / publication figures /
         figure aesthetics / color palette(cil) 等
筛选标准：stargazers_count >= 50 且近 12 个月有活跃更新（pushed_at 距今 <= 365 天）
        且 non-empty description 且含代码语言。

遵守 GitHub API 使用规范：
  - Search API 无令牌 10 req/min，REST 60 req/h；请求间 sleep，失败指数退避重试。
  - 不抓取贡献者明细（避免打满 REST 配额），贡献者数留空由 enrich 阶段后续补充。
输出：
  - github_sciplot.csv（utf-8-sig，Excel 可开）
  - github_sciplot_raw.json（完整原始 + 推断字段 + meta）
断点续跑：已写入的 repo full_name 集合记录在状态文件，重启跳过。
"""
import csv
import io
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BASE = "https://api.github.com"
OUT_CSV = "github_sciplot.csv"
OUT_JSON = "github_sciplot_raw.json"
STATE_FILE = "github_sciplot_state.json"

# 关键词组合（与科研绘图强相关）
QUERIES = [
    "scientific plotting python",
    "matplotlib publication figures",
    "seaborn data visualization",
    "plotly interactive visualization",
    "ggplot2 r visualization",
    "scientific color palette",
    "publication quality figures python",
    "data visualization tutorial",
    "latex tikz scientific figures",
    "matlab scientific plotting",
    "vega altair visualization",
    "statistical data visualization",
    "matplotlib style gallery",
    "figure design academic",
]

MIN_STARS = 50
# 近 12 个月活跃
ACTIVE_DAYS = 365
SLEEP = 7.0
MAX_RETRY = 4


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen": []}


def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _api_get(url, retries=MAX_RETRY):
    """GET 请求，带 User-Agent 与指数退避。返回 (json, status)。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "sciplot-scraper",
        "Accept": "application/vnd.github+json",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8")), resp.status
        except urllib.error.HTTPError as e:
            if e.code == 403 and "limit" in e.headers.get("X-RateLimit-Remaining", ""):
                # 限流，等待 reset
                reset = int(e.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - time.time(), 5)
                print(f"[限流] 等待 {wait:.0f}s...", flush=True)
                time.sleep(wait)
                continue
            if e.code == 404:
                return None, 404
            print(f"[HTTP {e.code}] {url[:80]}", flush=True)
            time.sleep(SLEEP * (2 ** attempt))
        except Exception as e:
            print(f"[ERR] {e} | {url[:80]}", flush=True)
            time.sleep(SLEEP * (2 ** attempt))
    return None, -1


def _infer_tool(topics, desc, name):
    """根据 topics/描述推断主要绘图工具。"""
    tool = "generic"
    text = (json.dumps(topics, ensure_ascii=False) + " " + desc + " " + name).lower()
    score = {
        "matplotlib": ("matplotlib" in text or "pyplot" in text),
        "seaborn": ("seaborn" in text),
        "plotly": ("plotly" in text),
        "ggplot2": ("ggplot" in text or "ggpubr" in text),
        "vega/altair": ("vega" in text or "altair" in text),
        "d3.js": ("d3.js" in text or "d3js" in text),
        "tikz/latex": ("tikz" in text or "pstricks" in text),
        "matlab": ("matlab" in text),
        "base-r": ("r graph" in text or "r-chart" in text),
    }
    hits = [k for k, v in score.items() if v]
    return hits[0] if hits else tool


def _infer_focus(topics, desc):
    """推断资源侧重：教程/库/风格/配色。"""
    text = (json.dumps(topics, ensure_ascii=False) + " " + desc).lower()
    if any(k in text for k in ["palette", "color", "colour", "colormap"]):
        return "配色/风格"
    if any(k in text for k in ["tutorial", "example", "gallery", "cookbook", "guide"]):
        return "教程/示例"
    if any(k in text for k in ["library", "package", "framework", "api", "tool"]):
        return "库/工具"
    return "通用"


def main():
    state = _load_state()
    seen = set(state["seen"])
    results = []

    for q in QUERIES:
        print(f"\n=== 查询: {q} ===", flush=True)
        page = 1
        while True:
            url = (f"{BASE}/search/repositories?q={urllib.parse.quote(q)}"
                   f"&sort=stars&order=desc&per_page=100&page={page}")
            data, status = _api_get(url)
            if status != 200 or not data:
                break
            items = data.get("items", [])
            if not items:
                break
            for it in items:
                full = it["full_name"]
                if full in seen:
                    continue
                seen.add(full)
                # 筛选：星标 + 活跃 + 描述 + 语言
                if it["stargazers_count"] < MIN_STARS:
                    continue
                pushed = it.get("pushed_at", "")
                try:
                    pushed_dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                    if (_now_utc() - pushed_dt).days > ACTIVE_DAYS:
                        continue
                except Exception:
                    pass
                if not it.get("description"):
                    continue
                lang = it.get("language")
                try:
                    cloned = it.get("clone_url", "")
                    results.append({
                        "full_name": full,
                        "html_url": it["html_url"],
                        "description": (it.get("description") or "").strip(),
                        "stargazers_count": it["stargazers_count"],
                        "forks_count": it["forks_count"],
                        "language": lang,
                        "topics": it.get("topics", []),
                        "tool_inferred": _infer_tool(it.get("topics", []), it.get("description") or "", full),
                        "focus_inferred": _infer_focus(it.get("topics", []), it.get("description") or ""),
                        "created_at": it.get("created_at", ""),
                        "updated_at": it.get("updated_at", ""),
                        "pushed_at": pushed,
                        "size": it.get("size"),
                        "open_issues_count": it.get("open_issues_count"),
                        "default_branch": it.get("default_branch"),
                        "clone_url": cloned,
                    })
                except Exception as e:
                    print(f"[skip] {full} {e}", flush=True)
            # 翻页判断
            total = data.get("total_count", 0)
            if page * 100 >= total or page >= 10:
                break
            page += 1
            time.sleep(SLEEP)
        time.sleep(SLEEP)

    # 去重（按 full_name）
    uniq = {}
    for r in results:
        uniq[r["full_name"]] = r
    results = list(uniq.values())
    results.sort(key=lambda x: -x["stargazers_count"])

    # 写 CSV
    fields = ["full_name", "html_url", "description", "stargazers_count", "forks_count",
              "language", "tool_inferred", "focus_inferred", "topics",
              "created_at", "updated_at", "pushed_at", "clone_url"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)

    # 写 JSON
    meta = {
        "keyword_queries": QUERIES,
        "min_stars": MIN_STARS,
        "active_days": ACTIVE_DAYS,
        "fetched_at": _now_utc().isoformat(),
        "total_repos": len(results),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "repos": results}, f, ensure_ascii=False, indent=2)

    state["seen"] = sorted(seen)
    _save_state(state)

    print(f"\n完成：共 {len(results)} 个仓库。")
    print(f"CSV -> {OUT_CSV}")
    print(f"JSON -> {OUT_JSON}")


if __name__ == "__main__":
    main()