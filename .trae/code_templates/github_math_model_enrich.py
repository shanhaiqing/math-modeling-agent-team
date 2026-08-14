# -*- coding: utf-8 -*-
"""
为抓取结果补充详情：贡献者数、主要建模方法、应用领域、项目结构推断。
- 贡献者数：逐项目 GET /repos/{full}/contributors?per_page=1 读 Link 分页头（仅 top N，控限流）
- 建模方法/应用领域：基于 topics + 语言 + 描述的关键词规则推断
- 输出：github_math_model_enriched.json + 更新 CSV
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import http.client
import csv
import re
import os
from datetime import datetime, timezone

USER_AGENT = "Mozilla/5.0 (math-model-research-scraper)"
API = "https://api.github.com"
TOP_N = 40          # 补充贡献者数的项目数（控 repo 限流 60/h）
REPO_SLEEP = 1.2

# 关键词 → 建模方法推断
METHOD_RULES = [
    (["integer", "milp", "ilp"], "整数规划 (MILP/ILP)"),
    (["linear-programming", "linear programming"], "线性规划 (LP)"),
    (["convex", "cvx", "convex-optimization"], "凸优化"),
    (["combinatorial", "constraint", "ortools", "or-tools"], "组合优化/约束求解"),
    (["metaheuristic", "genetic", "evolutionary", "particle", "simulated", "pso", "ga-", "ant-colony"], "元启发式算法"),
    (["agent-based", "tagents", "simulation", "abm"], "多智能体仿真 (ABM)"),
    (["neural", "deep-learning", "torch", "tensorflow", "pytorch"], "深度学习/神经网络"),
    (["statistic", "bayesian", "monte", "markov", "probabilistic"], "统计/概率建模"),
    (["graph", "network", "gephi"], "图论/网络建模"),
    (["game", "nash", "博弈"], "博弈论"),
    (["math", "mathematical-modeling", "model", "数学建模"], "数学建模"),
    (["optimization", "optimizer", "optimize"], "优化建模"),
]

# 关键词 → 应用领域
DOMAIN_RULES = [
    (["logistic", "supply", "routing", "vehicle", "tsp", "vrp"], "物流/运筹"),
    (["finance", "financial", "portfolio", "quant"], "金融/投资"),
    (["biology", "genetic", "epidem", "ecology", "bio"], "生物/生态"),
    (["energy", "power", "grid", "renewable", "wind", "solar"], "能源/电力"),
    (["transport", "traffic", "slocation", "rail"], "交通"),
    (["education", "course", "lesson", "竞赛"], "教学/竞赛"),
    (["game", "video", "engine"], "游戏"),
    (["manufacturing", "production", "scheduling", "industrial"], "制造/调度"),
    (["climate", "weather", "environment"], "气候/环境"),
    (["health", "medical", "hospital", "clinical"], "医疗健康"),
]

def api_get(url, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, "", e.headers
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionResetError, TimeoutError):
            time.sleep(5 * (a + 1))
    return None, "", None

def get_contributor_count(full_name):
    """通过 contributors?per_page=1 的 Link 分页头估计贡献者数"""
    url = f"{API}/repos/{urllib.parse.quote(full_name)}/contributors?per_page=1&anon=true"
    status, body, headers = api_get(url)
    if status != 200 or not headers:
        return None
    link = headers.get("Link", "")
    m = re.search(r'page=(\d+)>; rel="last"', link)
    return int(m.group(1)) if m else (1 if body.strip() != "[]" else 0)

def infer_methods(topics, lang, desc):
    text = " ".join(topics + [lang or "", desc or ""]).lower()
    out = []
    for keys, label in METHOD_RULES:
        if any(k.lower() in text for k in keys) and label not in out:
            out.append(label)
    return "; ".join(out[:3]) if out else "未推断"

def infer_domain(topics, desc):
    text = " ".join(topics + [desc or ""]).lower()
    out = []
    for keys, label in DOMAIN_RULES:
        if any(k.lower() in text for k in keys) and label not in out:
            out.append(label)
    return "; ".join(out[:3]) if out else ("教育/竞赛" if "数学建模" in text or "course" in text or "竞赛" in text or "model" in text else "通用")

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(out_dir, "github_math_model_raw.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]

    # 仅对 top N 补贡献者数（已补过的跳过）
    for i, it in enumerate(items[:TOP_N]):
        if it.get("contributors_count") is not None:
            continue
        cc = get_contributor_count(it["full_name"])
        it["contributors_count"] = cc
        print(f"[{i+1}/{min(TOP_N,len(items))}] {it['full_name']}: contributors={cc}")
        time.sleep(REPO_SLEEP)

    # 为全部补充方法与领域推断
    for it in items:
        it["method_inferred"] = infer_methods(it.get("topics", []), it.get("language"), it.get("description"))
        it["domain_inferred"] = infer_domain(it.get("topics", []), it.get("description"))
        # 项目结构：语言 + 默认分支 + 规模
        it["structure_note"] = f"primary_lang={it.get('language')}, default_branch={it.get('default_branch')}, size_kb={it.get('size')}"

    data["meta"]["contributors_enriched"] = min(TOP_N, len(items))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 写最终 CSV
    csv_path = os.path.join(out_dir, "github_math_model.csv")
    fields = ["full_name", "html_url", "description", "stargazers_count", "forks_count",
              "contributors_count", "language", "topics", "method_inferred", "domain_inferred",
              "structure_note", "created_at", "updated_at", "pushed_at", "size",
              "open_issues_count", "default_branch", "clone_url"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for it in items:
            it["topics"] = ",".join(it.get("topics", []))
            w.writerow(it)
    print(f"\n完成。enriched JSON + CSV 已更新，共 {len(items)} 项。")

if __name__ == "__main__":
    main()