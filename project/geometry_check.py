#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""geometry_check.py — 几何核验：坐标单位换算、目标节点、前线、连通性"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
DATA = os.path.join(HERE, "data")
FILE1 = os.path.join(DATA, "附件一：作战节点与通路数据.xlsx")
nodes = pd.read_excel(FILE1, sheet_name="节点信息")
edges = pd.read_excel(FILE1, sheet_name="通路信息")

pos = {int(r["节点编号"]): (float(r["横坐标X"]), float(r["纵坐标Y"])) for _, r in nodes.iterrows()}
camp = {int(r["节点编号"]): r["所属阵营"] for _, r in nodes.iterrows()}
defense = {int(r["节点编号"]): float(r["防御强度"]) for _, r in nodes.iterrows()}

# 1) 坐标单位 vs 链路长度：对每条边比较欧氏距离(坐标单位)与给定长度(km)
ratios = []
for _, e in edges.iterrows():
    a, b = int(e["起点编号"]), int(e["终点编号"])
    L = float(e["链路长度(km)"])
    d = np.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1])
    if d > 1e-9:
        ratios.append(L / d)
ratios = np.array(ratios)
print(f"链路长度/欧氏坐标距离 比值: mean={ratios.mean():.4f}, std={ratios.std():.4f}, "
      f"min={ratios.min():.4f}, max={ratios.max():.4f}, median={np.median(ratios):.4f}")

# 2) 目标节点
for nid in (352, 144, 149):
    print(f"节点{nid}: camp={camp.get(nid)}, pos={pos.get(nid)}, defense={defense.get(nid)}")

# 3) 阵营 Y 分布
sov = [pos[n][1] for n in camp if camp[n] == "苏军"]
all_y = [pos[n][1] for n in camp if camp[n] == "盟军"]
print(f"苏军 Y: min={min(sov):.2f}, max={max(sov):.2f}, mean={np.mean(sov):.2f}")
print(f"盟军 Y: min={min(all_y):.2f}, max={max(all_y):.2f}, mean={np.mean(all_y):.2f}")

# 4) 前线：跨阵营边
cross = [(int(e["起点编号"]), int(e["终点编号"]), float(e["链路长度(km)"]))
         for _, e in edges.iterrows()
         if camp[int(e["起点编号"])] != camp[int(e["终点编号"])]]
print(f"跨阵营边数: {len(cross)}")
cross_sorted = sorted(cross, key=lambda t: t[2])
print("最短跨阵营边(前10):", cross_sorted[:10])

# 5) 连通性（无向）
from collections import defaultdict, deque
adj = defaultdict(list)
for _, e in edges.iterrows():
    a, b = int(e["起点编号"]), int(e["终点编号"])
    adj[a].append(b); adj[b].append(a)
seen = set(); comps = []
for s in pos:
    if s not in seen:
        q = deque([s]); seen.add(s); comp = []
        while q:
            u = q.popleft(); comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); q.append(v)
        comps.append(comp)
print(f"连通分量数: {len(comps)}, 各分量大小: {sorted([len(c) for c in comps], reverse=True)[:10]}")
iso = [n for n in pos if not adj[n]]
print(f"孤立节点: {iso}")

# 6) 目标节点可达性
main_comp = max(comps, key=len)
for nid in (352, 144, 149):
    print(f"节点{nid} 在主分量中: {nid in main_comp}")

# 7) 战场尺度
xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
print(f"X范围 {min(xs):.1f}~{max(xs):.1f} (跨度{max(xs)-min(xs):.1f}), Y范围 {min(ys):.1f}~{max(ys):.1f} (跨度{max(ys)-min(ys):.1f})")
