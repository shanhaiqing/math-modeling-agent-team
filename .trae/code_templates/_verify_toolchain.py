# -*- coding: utf-8 -*-
"""一次性黄金对拍验证脚本（跑完即删）：CP-SAT vs pulp；networkx vs 手写 Dijkstra；max_flow 手算。"""
import math
import os
import sys
import heapq
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cp_solver
import graph_utils
from solver_backend import solve_mip, detect_backend

fails = []

# ============ 闸门2a: CP-SAT vs pulp（同一 0-1 背包，最优 10）============
prob = cp_solver.build_problem()
res_cp = cp_solver.solve_cp(prob)
res_pulp = solve_mip(prob)
print("CP-SAT:", res_cp["status"], res_cp["objective_value"], "gap", res_cp["MIPGap"])
print("pulp  :", res_pulp.status, res_pulp.objective_value, "gap", res_pulp.mip_gap)
ok_a = (res_cp["status"] == "optimal" and res_pulp.status == "optimal"
        and abs(res_cp["objective_value"] - 10.0) <= 1e-6
        and abs(res_pulp.objective_value - 10.0) <= 1e-6
        and abs(res_cp["objective_value"] - res_pulp.objective_value) <= 1e-6)
fails.append(("黄金对拍 CP-SAT vs pulp", ok_a))

# ============ 闸门2b: networkx 最短路 vs 手写 Dijkstra（期望 5）============
nodes, edges = graph_utils._demo_graph()
path_nx, dist_nx = graph_utils.shortest_path(nodes, edges, 1, 5)
adj = defaultdict(list)
for a, b, w in edges:
    adj[a].append((b, w)); adj[b].append((a, w))

def dijkstra_ref(src, dst):
    dist = {src: 0.0}; prev = {src: None}; pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if dst not in prev:
        return [], math.inf
    p = [dst]
    while prev[p[-1]] is not None:
        p.append(prev[p[-1]])
    return p[::-1], dist[dst]

path_ref, dist_ref = dijkstra_ref(1, 5)
print("networkx     :", path_nx, dist_nx)
print("手写Dijkstra :", path_ref, dist_ref)
ok_b = (path_nx == path_ref and abs(dist_nx - dist_ref) <= 1e-9 and dist_nx == 5.0)
fails.append(("黄金对拍 networkx vs 手写Dijkstra", ok_b))

# ============ 闸门2c: networkx 最大流 vs 手算（4 节点有向图，期望 4）============
# 边 (a,b,weight,capacity): 1→2:3, 1→3:2, 2→3:1, 2→4:2, 3→4:2
# 手算最大流：1→2→4(2) + 1→3→4(2) = 4；最小割 {1,2,3}|{4} = 2+2 = 4
mf_nodes = [1, 2, 3, 4]
mf_edges = [(1, 2, 1.0, 3), (1, 3, 1.0, 2), (2, 3, 1.0, 1), (2, 4, 1.0, 2), (3, 4, 1.0, 2)]
flow, flow_dict = graph_utils.max_flow(mf_nodes, mf_edges, 1, 4)
print("max_flow 1→4:", flow, "（期望 4）")
ok_c = abs(flow - 4.0) <= 1e-9
fails.append(("已知最优算例 max_flow", ok_c))

# ============ 闸门3: 老工具回归（solver_backend 仍可用）============
print("后端探测:", detect_backend())
ok_d = res_pulp.status == "optimal"
fails.append(("老工具回归 pulp", ok_d))

all_ok = True
for name, ok in fails:
    print(("[PASS] " if ok else "[FAIL] ") + name)
    all_ok = all_ok and ok
sys.exit(0 if all_ok else 1)
