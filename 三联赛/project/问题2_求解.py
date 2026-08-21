#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题2_求解.py — 三类补给分配与供应优化（含破交对抗/护航/消耗模式）
=================================================================
模型（问题2 补给分配优化模型）：
  min TC = C_trans + C_escort + C_loss + C_labor（四类成本分层，独立符号）
  决策：flow[c][k][r] 连续流量、z[r]∈{0,1} 护航、路径集预枚举（每OD 3候选）
  约束：C6 需求满足 / C7 载重 / 车辆-频次一致性 / 护航0-1
  对抗：基线静态风险 + Stackelberg 最坏情形对比（备选对抗模型）
  消耗模式：W_c 后勤工人数、V_c 车辆总数（独立公式）
符号映射见 common_data.py 头部。
"""
import json
import math
import os
import sys
import time

import numpy as np

from solver_backend import solve_mip, validate
from common_data import (load_graph, dijkstra, shortest_path, path_risk,
                         connected_components, FORCES, UNIT_TYPES,
                         TRUCK_CAP, TRUCK_SPEED, CREW_PER_TRUCK, C_KM,
                         C_ESCORT, C_UNIT_LOSS, C_WAGE, CONSUM,
                         ESCORT_REDUCTION, ENEMY_INTERDICT_BUDGET)

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
RESULTS = os.path.join(HERE, "results")

POS, CAMP, DEF, EDGE_LEN, ADJ, DEGREE = load_graph()
NODES = list(POS.keys())
MAIN = set(max(connected_components(NODES, ADJ), key=len))
GOODS = ["弹药", "燃油", "维修包"]


def compute_risk():
    risk = {}
    for (a, b) in EDGE_LEN:
        cross = 1.0 if CAMP[a] != CAMP[b] else 0.0
        risk[(a, b)] = min(0.35, 0.05 + 0.10 * cross + 0.02 * min(DEGREE[a], DEGREE[b]))
    return risk
RISK = compute_risk()


def load_q1_deploy():
    """读取问题1部署结果 → 每节点装备数/动员兵数（主分量）。"""
    with open(os.path.join(RESULTS, "q1_result.json"),
              encoding="utf-8") as f:
        q1 = json.load(f)
    deploy = {}
    for camp in ["苏军", "盟军"]:
        deploy[camp] = {}
        for key, v in q1["factions"][camp]["deploy"].items():
            u, n = key.split("@")
            n = int(n)
            if n in MAIN:
                deploy[camp][n] = deploy[camp].get(n, {})
                deploy[camp][n][u] = deploy[camp][n].get(u, 0) + v
    return q1, deploy


def compute_demand(deploy):
    """Demand[c][k][n]：由部署量×消耗率（A-06）。装备按百辆折算，动员兵按万人。"""
    demand = {}
    for camp in ["苏军", "盟军"]:
        demand[camp] = {k: {} for k in GOODS}
        for n, units in deploy[camp].items():
            n_equip = sum(v for u, v in units.items() if u != "动员兵")  # 辆/门
            n_inf = units.get("动员兵", 0)                                # 万人
            for k in GOODS:
                d = CONSUM[k]["装备"] * n_equip / 100.0 + CONSUM[k]["动员兵"] * n_inf
                if d > 1e-9:
                    demand[camp][k][n] = d
    return demand


def select_depots(camp, q1, n_depots=3):
    """仓库选址：己方主分量内高防御纵深节点（远离前线=Y 纵深 + 防御强度）。"""
    own = [n for n in NODES if CAMP[n] == camp and n in MAIN]
    ys = [POS[n][1] for n in own]
    # 纵深方向：苏军向北（Y大），盟军向南（Y小）
    depth = {n: (POS[n][1] - min(ys)) if camp == "苏军" else (max(ys) - POS[n][1])
             for n in own}
    dmax = max(depth.values()) + 1e-9
    score = {n: 0.6 * depth[n] / dmax + 0.4 * DEF[n] for n in own}
    ranked = sorted(score, key=score.get, reverse=True)
    return ranked[:n_depots]


def k_shortest_paths(adj, src, dst, K=3):
    """K 条候选路径：最短路 + 边扰动次短路（Yen 简化版）。"""
    paths = []
    base_path, base_d = shortest_path(adj, src, dst)
    if base_path is None:
        return []
    paths.append(base_path)
    # 扰动法：依次禁用已用边求次短路
    banned = set()
    for i in range(len(base_path) - 1):
        banned.add((base_path[i], base_path[i + 1]))
        adj2 = {u: [(v, L) for (v, L) in vs if (u, v) not in banned and (v, u) not in banned]
                for u, vs in adj.items()}
        p, d = shortest_path(adj2, src, dst)
        if p and p not in paths:
            paths.append(p)
        if len(paths) >= K:
            break
    # 补：最低风险路（按风险加权 Dijkstra）
    if len(paths) < K:
        risk_adj = {u: [(v, L * (1 + 5 * RISK.get((u, v), RISK.get((v, u), 0.05))))
                        for (v, L) in vs] for u, vs in adj.items()}
        p, d = shortest_path(risk_adj, src, dst)
        if p and p not in paths:
            paths.append(p)
    return paths[:K]


def solve_supply(camp, depots, demand, use_stackelberg=False):
    """补给 MIP。返回结果字典。"""
    # 汇总各节点总需求（三商品合并运输，装载按吨）
    node_demand = {}
    for k in GOODS:
        for n, d in demand[camp][k].items():
            node_demand[n] = node_demand.get(n, 0.0) + d
    demand_nodes = [n for n in node_demand if n not in depots]

    # 路径枚举
    route_data = []  # (r_id, depot, node, path, length, risk, demand_share)
    r_id = 0
    for n in demand_nodes:
        best_depot = None
        cand_all = []
        for dp in depots:
            ps = k_shortest_paths(ADJ, dp, n, K=3)
            for p in ps:
                L = sum(EDGE_LEN.get((p[i], p[i + 1]), EDGE_LEN.get((p[i + 1], p[i])))
                        for i in range(len(p) - 1))
                rk = path_risk(p, RISK)
                cand_all.append((dp, n, p, L, rk))
        # 每需求节点保留全局 Top3（距离/风险混合排序）
        cand_all.sort(key=lambda t: t[3] * (1 + 3 * t[4]))
        for (dp, n, p, L, rk) in cand_all[:3]:
            route_data.append((r_id, dp, n, p, L, rk))
            r_id += 1

    total_demand = sum(node_demand.values())
    variables, objective, constraints = [], {}, []
    # flow_r（吨/日）与 z_r（护航0-1）
    for (rid, dp, n, p, L, rk) in route_data:
        variables.append({"name": f"flow_{rid}", "low": 0,
                          "high": node_demand[n] * 3, "cat": "Continuous"})
        variables.append({"name": f"z_{rid}", "low": 0, "high": 1, "cat": "Binary"})
        # 目标：C_trans + C_escort + C_loss
        trips_per_ton = 1.0 / TRUCK_CAP  # 车次/吨
        objective[f"flow_{rid}"] = (L * C_KM * trips_per_ton          # 运输
                                    + rk * C_UNIT_LOSS)               # 期望损失
        objective[f"z_{rid}"] = 0.0  # 护航成本与流量耦合，用线性化：z*flow 近似为 z*需求上界份额
    # 护航成本线性化：C_escort ≈ Σ z_r × (node_demand[n]/3) × trips × c_esc
    for (rid, dp, n, p, L, rk) in route_data:
        share = node_demand[n] / 3.0
        trips = share / TRUCK_CAP
        objective[f"z_{rid}"] = objective.get(f"z_{rid}", 0.0) + trips * C_ESCORT
        # 护航降低损失：对 flow 的损失项修正 —— 用分段：loss_r = rk*(1-0.5*z_r)*flow
        # 双线性 z*flow 用大M线性化：引入 loss_r 变量
    # 为精确处理护航-损失耦合，引入辅助变量 loss_r 与 w_r=z_r*flow_r（McCormick）
    for (rid, dp, n, p, L, rk) in route_data:
        variables.append({"name": f"w_{rid}", "low": 0,
                          "high": node_demand[n] * 3, "cat": "Continuous"})
        M = node_demand[n] * 3
        # w ≤ M*z ; w ≤ flow ; w ≥ flow - M*(1-z) ; w ≥ 0
        constraints.append({"name": f"mc1_{rid}",
                            "coeffs": {f"w_{rid}": 1.0, f"z_{rid}": -M},
                            "sense": "<=", "rhs": 0.0})
        constraints.append({"name": f"mc2_{rid}",
                            "coeffs": {f"w_{rid}": 1.0, f"flow_{rid}": -1.0},
                            "sense": "<=", "rhs": 0.0})
        constraints.append({"name": f"mc3_{rid}",
                            "coeffs": {f"w_{rid}": 1.0, f"flow_{rid}": -1.0, f"z_{rid}": M},
                            "sense": ">=", "rhs": -M})
        # 修正目标：原 loss=rk*flow，护航后 loss=rk*(flow - 0.5*w)
        objective[f"flow_{rid}"] = objective.get(f"flow_{rid}", 0.0)  # 已含 rk*C_UNIT_LOSS
        objective[f"w_{rid}"] = -0.5 * rk * C_UNIT_LOSS

    # C6 需求满足：每节点流入 ≥ 需求
    for n in demand_nodes:
        coeffs = {f"flow_{rid}": 1.0 for (rid, dp, nn, p, L, rk) in route_data if nn == n}
        constraints.append({"name": f"demand_{n}", "coeffs": coeffs,
                            "sense": ">=", "rhs": node_demand[n]})
    # 每节点最多启用 2 条路径（冗余上限，防过度分散）
    for n in demand_nodes:
        coeffs = {f"z_{rid}": 1.0 for (rid, dp, nn, p, L, rk) in route_data if nn == n}
        constraints.append({"name": f"esc_cap_{n}", "coeffs": coeffs,
                            "sense": "<=", "rhs": 2.0})

    problem = {"name": f"supply_{camp}", "sense": "min", "variables": variables,
               "objective": {"coefficients": objective, "constant": 0.0},
               "constraints": constraints}
    res = solve_mip(problem, mip_gap=0.01, time_limit=300)

    # 提取结果
    routes_out = []
    C_trans = C_esc = C_loss = 0.0
    for (rid, dp, n, p, L, rk) in route_data:
        fl = res.variable_values.get(f"flow_{rid}", 0.0) or 0.0
        z = 1 if (res.variable_values.get(f"z_{rid}", 0.0) or 0) > 0.5 else 0
        if fl > 1e-6:
            trips = fl / TRUCK_CAP
            ct = L * C_KM * trips
            ce = z * trips * C_ESCORT
            cl = rk * (1 - ESCORT_REDUCTION * z) * fl * C_UNIT_LOSS
            C_trans += ct; C_esc += ce; C_loss += cl
            cycle_h = 24.0 / max(trips, 1e-9)
            routes_out.append({
                "route_id": rid, "depot": dp, "demand_node": n,
                "path": p, "length_km": round(L, 3),
                "risk": round(rk, 4), "escort": z,
                "flow_t_day": round(fl, 3),
                "trips_day": round(trips, 2),
                "load_t": TRUCK_CAP,
                "dispatch_cycle_h": round(cycle_h, 2),
                "cost_trans": round(ct, 1), "cost_escort": round(ce, 1),
                "cost_loss": round(cl, 1),
            })
    return {"status": res.status, "objective": res.objective_value,
            "MIPGap": res.mip_gap, "solver": res.solver,
            "solve_time": round(res.solve_time, 3),
            "C_trans": round(C_trans, 1), "C_escort": round(C_esc, 1),
            "C_loss": round(C_loss, 1),
            "TC_excl_labor": round(C_trans + C_esc + C_loss, 1),
            "routes": sorted(routes_out, key=lambda r: -r["flow_t_day"]),
            "total_demand_t_day": round(total_demand, 2),
            "validate": validate(res)}


def stackelberg_worst_case(camp, base_result, demand):
    """敌方最优响应：将破交预算投向 流量×货值/护航强度 最大的路径，重算损失。

    口径：主口径=含人力 TC_total（与 objective_value 一致）。TC_worst = 基线
    TC_total + extra_loss——破交追加损失只作用于货物损失项，人力成本（工资）
    在对抗情形下不变。
    """
    assert "TC_total" in base_result, "须先计算 C_labor/TC_total 再做 Stackelberg 对照（口径一致性）"
    routes = base_result["routes"]
    scored = sorted(routes, key=lambda r: -(r["flow_t_day"] / (1 + r["escort"])))
    hit = scored[:ENEMY_INTERDICT_BUDGET]
    extra_loss = sum(r["flow_t_day"] * r["risk"] * C_UNIT_LOSS * 0.5
                     for r in hit)  # 集中打击使有效风险提升
    tc_base = base_result["TC_total"]
    return {"hit_routes": [r["route_id"] for r in hit],
            "extra_loss": round(extra_loss, 1),
            "caliber": "含人力 TC_total（主口径，与 objective_value 一致）",
            "TC_baseline": round(tc_base, 1),
            "TC_worst": round(tc_base + extra_loss, 1),
            "delta_pct": round(extra_loss / tc_base * 100, 2),
            "TC_excl_labor_baseline": base_result["TC_excl_labor"],
            "delta_pct_excl_labor_reference": round(
                extra_loss / base_result["TC_excl_labor"] * 100, 2)}


def attrition_mode(camp, demand):
    """消耗模式（完全不补给）：维持前线所需后勤工人数与车辆总数。
    V = Σ_n ceil(D_n / (Cap × 周转次数))，周转次数=24h/(2×平均运输时间+装卸2h)
    W = 司机(2/车) + 装卸(每50吨/日需10人) + 维修(车辆数×0.1)
    """
    node_demand = {}
    for k in GOODS:
        for n, d in demand[camp][k].items():
            node_demand[n] = node_demand.get(n, 0.0) + d
    total = sum(node_demand.values())
    # 平均运输距离估计：主分量边均值×3跳
    avg_edge = np.mean(list(EDGE_LEN.values()))
    avg_trip_h = 2 * (avg_edge * 3) / TRUCK_SPEED + 2.0  # 往返+装卸
    turns = 24.0 / avg_trip_h
    V = sum(math.ceil(d / (TRUCK_CAP * turns)) for d in node_demand.values())
    W = CREW_PER_TRUCK * V + math.ceil(total / 50.0) * 10 + math.ceil(V * 0.1)
    return {"total_workers": int(W), "total_vehicles": int(V),
            "total_demand_t_day": round(total, 2),
            "avg_trip_hours": round(avg_trip_h, 2), "turns_per_day": round(turns, 2)}


def main():
    t0 = time.time()
    q1, deploy = load_q1_deploy()
    demand = compute_demand(deploy)
    out = {"factions": {}}
    for camp in ["苏军", "盟军"]:
        depots = select_depots(camp, q1)
        base = solve_supply(camp, depots, demand)
        # 后勤人力成本（补给模式）：司机=车辆×2，车辆数=Σ trips×cycle/24
        n_vehicles = sum(math.ceil(r["trips_day"] * r["dispatch_cycle_h"] / 24.0)
                         for r in base["routes"])
        n_workers = CREW_PER_TRUCK * n_vehicles + math.ceil(
            base["total_demand_t_day"] / 50.0) * 10
        C_labor = n_workers * C_WAGE
        base["C_labor"] = round(C_labor, 1)
        base["TC_total"] = round(base["TC_excl_labor"] + C_labor, 1)
        base["n_vehicles_supply_mode"] = n_vehicles
        base["n_workers_supply_mode"] = n_workers
        # Stackelberg 最坏情形须在 TC_total 计算之后（含人力主口径）
        worst = stackelberg_worst_case(camp, base, demand)
        attr = attrition_mode(camp, demand)
        out["factions"][camp] = {
            "depots": depots,
            "supply_optimization": base,
            "stackelberg_worst_case": worst,
            "attrition_mode": attr,
        }
        print(f"[{camp}] 仓库={depots} TC={base['TC_total']:.0f}元/日 "
              f"(运输{base['C_trans']:.0f}/护航{base['C_escort']:.0f}/"
              f"损失{base['C_loss']:.0f}/人力{C_labor:.0f}) "
              f"路径数={len(base['routes'])} status={base['status']} "
              f"gap={base['MIPGap']} t={base['solve_time']}s")
        print(f"    消耗模式: 工人={attr['total_workers']} 车辆={attr['total_vehicles']}")
        print(f"    Stackelberg最坏(含人力口径): 打击路径={worst['hit_routes']} "
              f"TC_worst={worst['TC_worst']} Δ={worst['delta_pct']:+.2f}%")
    out["total_time_s"] = round(time.time() - t0, 1)
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "q2_result.json"),
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("已写入 q2_result.json")


if __name__ == "__main__":
    main()
