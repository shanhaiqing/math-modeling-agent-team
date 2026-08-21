#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题1_求解.py — 双方兵力部署优化 + 前线指挥节点选址 + 防空配置
=================================================================
模型（问题1 部署优化模型）：
  max Φ_c = 0.5*(F/F_max) + 0.3*(S/S_max) - 0.2*(D/D_max)
  F = Σ_m v_m·y_m（y_m=min(覆盖数,3) 有效覆盖，边际递减）
  S = Σ_{u,n} d_n·surv_u·x[u][n]（生存效能）
  D = Σ_{u,n} x[u][n]·dist(n,z)/N_total（指挥通信距离，z=候选指挥节点）
约束：C1仅己方节点 / C2兵力守恒 / C3防空=10(独立) / C4空中≤10% /
      C5咽喉覆盖≥1 / P2节点容量≤15% / C9非负整数
指挥节点：多准则评分 Top6 候选 → 逐候选 MIP → 最优为主选+3备选
防空：Stage B 最大覆盖 MIP（10 据点覆盖已部署兵力，与部署阶段解耦）
符号映射见 common_data.py 头部。求解器 solver_backend.solve_mip（HiGHS/CBC）。
"""
import json
import os
import sys
import time

import numpy as np

from solver_backend import solve_mip, validate
from common_data import (load_graph, dijkstra, euclid, connected_components,
                         cross_faction_edges, FORCES, UNIT_TYPES, N_AA,
                         AIR_CAP_RATIO, RANGE, ARTILLERY_RANGE, FIREPOWER,
                         SURV, R_AA, AA_SURV_BONUS, COVER_CAP, NODE_CAP_RATIO,
                         W_COVER, TARGET_NODES)

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
RESULTS = os.path.join(HERE, "results")

POS, CAMP, DEF, EDGE_LEN, ADJ, DEGREE = load_graph()
NODES = list(POS.keys())
COMPS = connected_components(NODES, ADJ)
MAIN = set(max(COMPS, key=len))

# 全图最短路直径 D_max（主分量采样估计，作 D 归一化尺度）
def estimate_diameter(sample=40):
    rng = np.random.default_rng(42)
    samp = rng.choice(sorted(MAIN), size=min(sample, len(MAIN)), replace=False)
    dmax = 0.0
    for s in samp:
        d = dijkstra(ADJ, int(s), MAIN)
        dmax = max(dmax, max(d.values()))
    return dmax
D_MAX = estimate_diameter()


def unit_range(camp, u):
    if u == "火炮":
        return ARTILLERY_RANGE[camp]
    return RANGE[u]


def build_coverage(camp):
    """稀疏覆盖系数 cov：(u,n,m)→1 若单位u在己方节点n射程内覆盖敌节点m。"""
    own = [n for n in NODES if CAMP[n] == camp]
    enemy = [m for m in NODES if CAMP[m] != camp]
    cov = {u: {} for u in UNIT_TYPES}   # cov[u][(n,m)]=1
    for u in UNIT_TYPES:
        r = unit_range(camp, u)
        if r <= 0:
            continue
        for n in own:
            for m in enemy:
                if euclid(POS, n, m) <= r:
                    cov[u][(n, m)] = 1
    return own, enemy, cov


def command_candidates(camp, k=6):
    """多准则评分选指挥节点候选：通信0.4/隐蔽0.3/抗毁0.3（代理指标）。"""
    own = [n for n in NODES if CAMP[n] == camp and n in MAIN]
    # 己方部署重心（用防御强度加权位置近似）
    wx = sum(POS[n][0] * DEF[n] for n in own) / sum(DEF[n] for n in own)
    wy = sum(POS[n][1] * DEF[n] for n in own) / sum(DEF[n] for n in own)
    scores = {}
    maxd = max(euclid(POS, n, None) if False else
               np.hypot(POS[n][0] - wx, POS[n][1] - wy) for n in own)
    for n in own:
        comm = 1.0 - np.hypot(POS[n][0] - wx, POS[n][1] - wy) / maxd  # 靠近重心=通信好
        conceal = 1.0 - DEF[n] * 0.5 - min(DEGREE[n], 6) / 6 * 0.5     # 低暴露=隐蔽
        resist = DEF[n]                                                # 防御=抗毁
        scores[n] = 0.4 * comm + 0.3 * conceal + 0.3 * resist
    ranked = sorted(scores, key=scores.get, reverse=True)
    return ranked[:k], scores


def solve_deployment(camp, cmd_node, own, enemy, cov, dist_to_cmd):
    """给定指挥节点，求解部署 MIP。返回 SolveResult + 结构化解。"""
    N = FORCES[camp]
    F_max = sum(DEF[m] for m in enemy) * COVER_CAP
    S_max = sum(N[u] * SURV[u] for u in UNIT_TYPES)
    N_total = sum(N.values())
    w1, w2, w3 = W_COVER

    variables, objective = [], {}
    # x[u][n]
    for u in UNIT_TYPES:
        cap = max(1, int(NODE_CAP_RATIO * N[u]))
        for n in own:
            name = f"x_{u}_{n}"
            variables.append({"name": name, "low": 0, "high": cap, "cat": "Integer"})
    # y_m 有效覆盖
    for m in enemy:
        variables.append({"name": f"y_{m}", "low": 0, "high": COVER_CAP, "cat": "Continuous"})

    # 目标
    for m in enemy:
        objective[f"y_{m}"] = w1 * DEF[m] / F_max
    for u in UNIT_TYPES:
        for n in own:
            objective[f"x_{u}_{n}"] = (w2 * DEF[n] * SURV[u] / S_max
                                       - w3 * dist_to_cmd[n] / (N_total * D_MAX))

    constraints = []
    # C2 兵力守恒（地面单位全部署；空中单位按 C4 上限不等式，其余留预备队）
    for u in UNIT_TYPES:
        if u == "空中":
            constraints.append({"name": f"force_{u}",
                                "coeffs": {f"x_{u}_{n}": 1.0 for n in own},
                                "sense": "<=", "rhs": float(N[u] * AIR_CAP_RATIO)})
        else:
            constraints.append({"name": f"force_{u}",
                                "coeffs": {f"x_{u}_{n}": 1.0 for n in own},
                                "sense": "==", "rhs": float(N[u])})
    # C4 空中上限：已并入 force_空中 不等式（rhs=N*10%）
    # C5 咽喉覆盖：每条跨阵营边的敌方端点须被≥1火力覆盖（按边索引命名，端点可重复）
    for ei, (a, b, L) in enumerate(cross_faction_edges(EDGE_LEN, CAMP)):
        m = b if CAMP[b] != camp else a   # 敌方端点
        coeffs = {}
        for u in UNIT_TYPES:
            for n in own:
                if (n, m) in cov[u]:
                    coeffs[f"x_{u}_{n}"] = coeffs.get(f"x_{u}_{n}", 0.0) + 1.0
        if coeffs:
            constraints.append({"name": f"throat_e{ei}_n{m}", "coeffs": coeffs,
                                "sense": ">=", "rhs": 1.0})
    # y_m ≤ Σ cov·x（有效覆盖不超过实际覆盖）
    for m in enemy:
        coeffs = {f"y_{m}": 1.0}
        for u in UNIT_TYPES:
            for n in own:
                if (n, m) in cov[u]:
                    coeffs[f"x_{u}_{n}"] = coeffs.get(f"x_{u}_{n}", 0.0) - 1.0
        constraints.append({"name": f"cover_{m}", "coeffs": coeffs,
                            "sense": "<=", "rhs": 0.0})

    problem = {"name": f"deploy_{camp}", "sense": "max", "variables": variables,
               "objective": {"coefficients": objective, "constant": 0.0},
               "constraints": constraints}
    res = solve_mip(problem, mip_gap=0.01, time_limit=300)
    return res, {"F_max": F_max, "S_max": S_max, "N_total": N_total}


def place_aa(camp, deploy, own):
    """Stage B：10 个防空据点最大覆盖已部署兵力（权重=部署量×生存系数）。"""
    # 候选：己方节点；覆盖：R_AA 内的部署节点
    weight = {}
    for n in own:
        w = sum(deploy.get((u, n), 0) * SURV[u] for u in UNIT_TYPES)
        if w > 0:
            weight[n] = w
    cand = list(weight.keys())
    cover = {p: [n for n in weight if euclid(POS, p, n) <= R_AA] for p in cand}
    variables = [{"name": f"aa_{p}", "low": 0, "high": 1, "cat": "Binary"} for p in cand]
    variables += [{"name": f"cov_{n}", "low": 0, "high": 1, "cat": "Continuous"} for n in weight]
    objective = {f"cov_{n}": weight[n] for n in weight}
    constraints = [{"name": "aa_num", "coeffs": {f"aa_{p}": 1.0 for p in cand},
                    "sense": "==", "rhs": float(N_AA)}]
    for n in weight:
        coeffs = {f"cov_{n}": 1.0}
        for p in cover:
            if n in cover[p]:
                coeffs[f"aa_{p}"] = coeffs.get(f"aa_{p}", 0.0) - 1.0
        constraints.append({"name": f"aa_cover_{n}", "coeffs": coeffs,
                            "sense": "<=", "rhs": 0.0})
    problem = {"name": f"aa_{camp}", "sense": "max", "variables": variables,
               "objective": {"coefficients": objective, "constant": 0.0},
               "constraints": constraints}
    res = solve_mip(problem, mip_gap=0.01, time_limit=120)
    aa_nodes = [p for p in cand if res.variable_values.get(f"aa_{p}", 0) > 0.5]
    return aa_nodes, res


def main():
    t0 = time.time()
    results = {}
    for camp in ["苏军", "盟军"]:
        own, enemy, cov = build_coverage(camp)
        cands, scores = command_candidates(camp, k=6)
        # 预计算各候选指挥节点的最短路距离
        best = None
        cand_results = {}
        for z in cands:
            dist_z = dijkstra(ADJ, z, MAIN)
            dist_to_cmd = {n: dist_z.get(n, D_MAX) for n in own}
            res, meta = solve_deployment(camp, z, own, enemy, cov, dist_to_cmd)
            probs = validate(res)
            cand_results[z] = {"obj": res.objective_value, "status": res.status,
                               "gap": res.mip_gap, "time": res.solve_time,
                               "problems": probs}
            if res.status in ("optimal", "feasible"):
                score = res.objective_value
                if best is None or score > best[1]:
                    best = (z, score, res, meta, dist_to_cmd)
        z, obj, res, meta, dist_to_cmd = best
        # 提取部署
        deploy = {}
        for u in UNIT_TYPES:
            for n in own:
                v = res.variable_values.get(f"x_{u}_{n}", 0.0)
                if v and v > 1e-6:
                    deploy[(u, n)] = int(round(v))
        # 防空
        aa_nodes, aa_res = place_aa(camp, deploy, own)
        # 计算 F/S/D 明细
        F = sum(DEF[m] * min(sum(deploy.get((u, n), 0) for u in UNIT_TYPES
                                 for n in own if (n, m) in cov[u]), COVER_CAP)
                for m in enemy)
        S_base = sum(DEF[n] * SURV[u] * deploy.get((u, n), 0)
                     for u in UNIT_TYPES for n in own)
        # 防空加成
        aa_covered = set()
        for p in aa_nodes:
            for n in own:
                if euclid(POS, p, n) <= R_AA:
                    aa_covered.add(n)
        S_bonus = sum(DEF[n] * SURV[u] * deploy.get((u, n), 0) * AA_SURV_BONUS
                      for u in UNIT_TYPES for n in aa_covered)
        N_total = meta["N_total"]
        D = sum(deploy.get((u, n), 0) * dist_to_cmd[n]
                for u in UNIT_TYPES for n in own) / N_total
        # 指挥节点备选（评分 Top，排除主选）
        backups = [n for n in cands if n != z][:3]
        # 活跃约束提取
        active = [c for c in res.active_constraints if c["active"]]
        results[camp] = {
            "command_node": z, "command_backups": backups,
            "command_scores": {str(n): round(scores[n], 4) for n in cands},
            "objective_value": round(obj, 6),
            "F": round(F, 3), "S_base": round(S_base, 3),
            "S_bonus": round(S_bonus, 3), "S_total": round(S_base + S_bonus, 3),
            "D_km": round(D, 3), "D_norm": round(D / D_MAX, 4),
            "deploy": {f"{u}@{n}": v for (u, n), v in sorted(deploy.items())},
            "deploy_node_count": len(set(n for (_, n) in deploy)),
            "aa_nodes": sorted(aa_nodes),
            "aa_objective": round(aa_res.objective_value, 3) if aa_res.objective_value else None,
            "solver": res.solver, "status": res.status, "MIPGap": res.mip_gap,
            "solve_time": round(res.solve_time, 3),
            "n_active_constraints": len(active),
            "active_constraints_sample": active[:20],
            "candidate_eval": {str(k): v for k, v in cand_results.items()},
            "validate_problems": validate(res),
        }
        print(f"[{camp}] 指挥节点={z} 备选={backups} Φ={obj:.4f} "
              F"F={F:.1f} S={S_base + S_bonus:.1f} D={D:.2f}km "
              f"部署节点数={len(set(n for (_, n) in deploy))} 防空={sorted(aa_nodes)} "
              f"status={res.status} gap={res.mip_gap} t={res.solve_time:.1f}s")

    out = {"D_MAX_km": round(D_MAX, 3), "factions": results,
           "total_time_s": round(time.time() - t0, 1)}
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "q1_result.json"),
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("已写入 q1_result.json，总耗时", out["total_time_s"], "s")


if __name__ == "__main__":
    main()
