#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common_data.py — 共享数据层：战场网络加载、图算法、参数预计算
=================================================================
符号映射（赛题参数 → 代码变量名）：
  节点n/阵营c/单位u → node_id / camp / unit_type
  d_n(防御强度)     → defense[n]
  camp(n)           → camp[n]
  L_e(链路长度km)   → edge_len[(a,b)]
  N[c][u](总兵力)   → FORCES[c][u]
  R_u(射程)         → RANGE[u]
  risk_e(破交概率)  → risk[e]
  T(转移目标)       → TARGET_NODES = [352, 144, 149]
坐标单位=km（几何核验：603 条边 长度/欧氏距离 比值恒 1.0000）。
"""
import heapq
import math
import os
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
DATA = os.path.join(HERE, "data")
RESULTS = os.path.join(HERE, "results")
FIGDIR = os.path.join(HERE, "figures")
FILE1 = os.path.join(DATA, "附件一：作战节点与通路数据.xlsx")

# ---------------- 题目原文参数（与赛题原文逐字对应） ----------------
FORCES = {
    "苏军": {"动员兵": 125, "轻型": 420, "中型": 300, "重型": 180, "火炮": 7000, "空中": 500},
    "盟军": {"动员兵": 100, "轻型": 800, "中型": 570, "重型": 340, "火炮": 14000, "空中": 300},
}  # 动员兵单位=万人（A-07），其余=辆/门/架
UNIT_TYPES = ["动员兵", "轻型", "中型", "重型", "火炮", "空中"]
N_AA = 10                      # 每方防空据点数（题目）
AIR_CAP_RATIO = 0.10           # A-04 空中单位部署上限
TARGET_NODES = [352, 144, 149]  # 盟军战略转移目标（题目）

# 射程 km：火炮=附件二最大射程（题目）；坦克直射=假设 A-02；动员兵=0（无火力覆盖贡献）
RANGE = {"动员兵": 0.0, "轻型": 1.5, "中型": 2.0, "重型": 2.0, "火炮": None, "空中": 0.0}
ARTILLERY_RANGE = {"苏军": 16.8, "盟军": 13.0}   # V3 16.8km / 光棱火炮 13.0km（附件二）

# 火力强度权重 alpha_u（A-05 Lanchester 标定同源）
FIREPOWER = {"动员兵": 0.2, "轻型": 0.3, "中型": 0.7, "重型": 1.0, "火炮": 0.8, "空中": 0.5}
# 基础生存系数 surv_u（估计：按装甲/隐蔽，经验估计）
SURV = {"动员兵": 0.4, "轻型": 0.6, "中型": 0.7, "重型": 0.85, "火炮": 0.5, "空中": 0.3}

R_AA = 3.0          # A-03 防空覆盖半径 km
AA_SURV_BONUS = 0.2  # 防空覆盖内生存提升
COVER_CAP = 3       # 单目标有效覆盖次数上限（边际递减）
NODE_CAP_RATIO = 0.15  # P2 单节点部署上限=该类型总量15%
W_COVER = (0.5, 0.3, 0.2)  # w1,w2,w3（按题目语义排序）

# Q2 后勤参数（A-06）
TRUCK_CAP = 10.0        # 吨/车
TRUCK_SPEED = 40.0      # km/h
CREW_PER_TRUCK = 2      # 司机/车
C_KM = 20.0             # 元/km·车
C_ESCORT = 500.0        # 元/车次
C_UNIT_LOSS = 1000.0    # 元/吨（破交损失货值）
C_WAGE = 300.0          # 元/人·日
# 日消耗率：吨/百辆（装备）与 吨/万人（动员兵）
CONSUM = {"弹药": {"装备": 0.8, "动员兵": 0.3},
          "燃油": {"装备": 0.6, "动员兵": 0.15},
          "维修包": {"装备": 0.2, "动员兵": 0.05}}
ESCORT_REDUCTION = 0.5   # 护航损失削减（A-01）
ENEMY_INTERDICT_BUDGET = 5  # Stackelberg 敌方破交预算（条路径）


def load_graph():
    """加载附件一，返回节点/边结构。含数据规模断言（题目原文回读，436行/603行）。"""
    nodes = pd.read_excel(FILE1, sheet_name="节点信息")
    edges = pd.read_excel(FILE1, sheet_name="通路信息")
    assert len(nodes) == 436, f"附件一节点行数应为436，实际{len(nodes)}"
    assert len(edges) == 603, f"附件一通路行数应为603，实际{len(edges)}"
    pos, camp, defense, degree = {}, {}, {}, defaultdict(int)
    for _, r in nodes.iterrows():
        n = int(r["节点编号"])
        pos[n] = (float(r["横坐标X"]), float(r["纵坐标Y"]))
        camp[n] = r["所属阵营"]
        defense[n] = float(r["防御强度"])
    edge_len, adj = {}, defaultdict(list)
    for _, r in edges.iterrows():
        a, b, L = int(r["起点编号"]), int(r["终点编号"]), float(r["链路长度(km)"])
        edge_len[(a, b)] = L
        adj[a].append((b, L)); adj[b].append((a, L))
        degree[a] += 1; degree[b] += 1
    return pos, camp, defense, edge_len, adj, dict(degree)


def euclid(pos, a, b):
    return math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1])


def dijkstra(adj, src, node_set=None):
    """单源最短路（边权=链路长度 km）。返回 {node: dist}。"""
    dist = {src: 0.0}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        for v, L in adj[u]:
            if node_set is not None and v not in node_set:
                continue
            nd = d + L
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


def shortest_path(adj, src, dst):
    """最短路 + 路径节点序列。"""
    dist = {src: 0.0}; prev = {src: None}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == dst:
            break
        if d > dist.get(u, math.inf):
            continue
        for v, L in adj[u]:
            nd = d + L
            if nd < dist.get(v, math.inf):
                dist[v] = nd; prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dst not in prev:
        return None, math.inf
    path = [dst]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return path[::-1], dist[dst]


def connected_components(nodes, adj):
    """BFS 连通分量。"""
    seen, comps = set(), []
    for s in nodes:
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            u = stack.pop(); comp.append(u)
            for v, _ in adj[u]:
                if v not in seen:
                    seen.add(v); stack.append(v)
        comps.append(comp)
    return comps


def compute_risk(edge_len, adj, degree, camp):
    """A-01 破交拦截概率：risk_e = min(0.35, 0.05 + 0.10*跨阵营 + 0.02*min(端点度数))。"""
    risk = {}
    for (a, b) in edge_len:
        cross = 1.0 if camp[a] != camp[b] else 0.0
        risk[(a, b)] = min(0.35, 0.05 + 0.10 * cross + 0.02 * min(degree[a], degree[b]))
    return risk


def path_risk(path, risk):
    """路径拦截概率 ≈ 1 - Π(1-risk_e)。"""
    p_safe = 1.0
    for i in range(len(path) - 1):
        e = (path[i], path[i + 1])
        r = risk.get(e, risk.get((e[1], e[0]), 0.05))
        p_safe *= (1.0 - r)
    return 1.0 - p_safe


def cross_faction_edges(edge_len, camp):
    """8 条跨阵营边（前线咽喉）。"""
    return [(a, b, L) for (a, b), L in edge_len.items() if camp[a] != camp[b]]


if __name__ == "__main__":
    pos, camp, defense, edge_len, adj, degree = load_graph()
    comps = connected_components(pos.keys(), adj)
    risk = compute_risk(edge_len, adj, degree, camp)
    print(f"节点{len(pos)} 边{len(edge_len)} 分量{[len(c) for c in comps]}")
    print(f"跨阵营边{len(cross_faction_edges(edge_len, camp))}条")
    print(f"risk 均值{np.mean(list(risk.values())):.4f}")
    # 主分量核验
    main = max(comps, key=len)
    assert all(t in main for t in TARGET_NODES), "目标节点须在主分量"
    print("目标节点均在主分量 ✓")
