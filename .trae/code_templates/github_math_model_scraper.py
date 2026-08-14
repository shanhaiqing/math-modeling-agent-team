# -*- coding: utf-8 -*-
"""
GitHub 数模项目抓取脚本
- 策略：多关键词组合，每个关键词 1 次 Search API 请求（per_page=100，取 top 命中）
          本地按筛选规则过滤，请求间 sleep 控制限流（无令牌 search 限流 10 次/分钟）
- 输出：抓取结果 JSON + 筛选后 CSV
- 用法：python github_math_model_scraper.py
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import http.client
import csv
import os
from datetime import datetime, timezone

USER_AGENT = "Mozilla/5.0 (math-model-research-scraper)"
BASE = "https://api.github.com/search/repositories"

# 筛选规则
MIN_STARS = 50                     # 星标下限
RECENT_DAYS = 365                  # 近12个月活跃（按 pushed_at）
SLEEP = 7.0                        # 请求间隔（秒），规避 search 限流 10/min

# 关键词组合（覆盖英文/中文/方法/领域）
KEYWORDS = [
    "mathematical modeling",
    "mathematical modelling",
    "math model",
    "数学建模",
    "operations research",
    "optimization modeling",
    "integer programming",
    "linear programming",
    "simulation modeling",
]

def api_get(url, retries=4):
    """发送 GET 请求，返回 (status, json_dict, rate_remaining)；网络中断自动重试"""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8")
                rem = r.headers.get("X-RateLimit-Remaining")
                return r.status, json.loads(body), rem
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            return e.code, {"error": body}, e.headers.get("X-RateLimit-Remaining") if e.headers else None
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionResetError, TimeoutError) as e:
            print(f"  网络异常({type(e).__name__})，第 {attempt+1}/{retries} 次重试")
            time.sleep(8 * (attempt + 1))
    return None, {"error": "persistent network failure"}, None

def is_recent(pushed_at, recent_days):
    """近 N 个月是否有活跃更新"""
    try:
        dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days <= recent_days
    except Exception:
        return False

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(out_dir, "github_math_model_raw.json")

    # 断点续跑：读取已有结果与已处理关键词
    results = []
    done_kw = set()
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
            results = [it for it in prev.get("items", []) if not it.get("_recent_saved")]
            done_kw = set(prev.get("_done_keywords", []))
            print(f"断点续跑：已加载 {len(results)} 项历史结果，已处理 {len(done_kw)} 个关键词")
        except Exception as e:
            print(f"历史文件读取失败，全新开始: {e}")

    seen = set(r["full_name"] for r in results)

    for kw in KEYWORDS:
        if kw in done_kw:
            continue
        q = urllib.parse.quote(f"{kw} stars:>={MIN_STARS}")
        url = f"{BASE}?q={q}&sort=stars&order=desc&per_page=100"
        status, data, rem = api_get(url)
        print(f"[{kw}] status={status} remaining={rem} total={data.get('total_count') if isinstance(data,dict) else 'ERR'}")
        if status == 200 and isinstance(data, dict):
            for it in data.get("items", []):
                full = it["full_name"]
                if full not in seen:
                    seen.add(full)
                    it["_has_doc"] = bool((it.get("description") or "").strip())
                    it["_recent"] = is_recent(it.get("pushed_at", ""), RECENT_DAYS)
                    it["_recent_saved"] = False
                    results.append(it)
            done_kw.add(kw)
        elif status == 403:
            print("  限流触发，等待 60s 后继续")
            time.sleep(60)
        else:
            print(f"  请求失败: {data}")
        # 每处理完一个关键词即落盘，防中断丢失
        _save_progress(json_path, results, done_kw)
        time.sleep(SLEEP)

    # 应用筛选：近12月活跃 + 有文档
    filtered = [r for r in results if r["_recent"] and r["_has_doc"]]
    filtered.sort(key=lambda x: x["stargazers_count"], reverse=True)

    # 保存 JSON（移除 _recent_saved 标记）
    for r in results:
        r.pop("_recent_saved", None)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "scrape_time": datetime.now(timezone.utc).isoformat(),
                "min_stars": MIN_STARS,
                "recent_days": RECENT_DAYS,
                "keywords": KEYWORDS,
                "total_raw_unique": len(results),
                "total_filtered": len(filtered),
            },
            "items": filtered,
        }, f, ensure_ascii=False, indent=2)

    # 保存 CSV（精简字段）
    csv_path = os.path.join(out_dir, "github_math_model.csv")
    fields = ["full_name", "html_url", "description", "stargazers_count",
              "forks_count", "language", "topics", "created_at", "updated_at",
              "pushed_at", "size", "open_issues_count", "default_branch", "clone_url"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in filtered:
            r["topics"] = ",".join(r.get("topics", []))
            w.writerow(r)

    print(f"\n完成。原始去重 {len(results)} 项，筛选后 {len(filtered)} 项。")
    print(f"JSON: {json_path}")
    print(f"CSV : {csv_path}")

def _save_progress(json_path, results, done_kw):
    """每处理完一个关键词落盘，防中断丢失；不删除已保存项"""
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "_done_keywords": sorted(done_kw),
                "items": results,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"进度落盘失败: {e}")

if __name__ == "__main__":
    main()