# -*- coding: utf-8 -*-
"""github_sciplot_analyze.py — 分析抓取结果概览"""
import csv
import collections

rows = list(csv.DictReader(open(".trae/code_templates/github_sciplot.csv", encoding="utf-8-sig")))
print("总数:", len(rows))
print("--- 工具分布 ---")
for k, v in collections.Counter(r["tool_inferred"] for r in rows).most_common():
    print(f"  {k}: {v}")
print("--- 侧重分布 ---")
for k, v in collections.Counter(r["focus_inferred"] for r in rows).most_common():
    print(f"  {k}: {v}")
print("--- 语言 Top8 ---")
for k, v in collections.Counter(r["language"] for r in rows).most_common(8):
    print(f"  {k}: {v}")
print("--- 最高星标 Top12 ---")
for r in sorted(rows, key=lambda x: -int(x["stargazers_count"]))[:12]:
    print(f"  {r['stargazers_count']:>6}  {r['full_name']}")