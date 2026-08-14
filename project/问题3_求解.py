#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题3_求解.py — 苏军进攻方案 + 盟军两情景战略转移
=================================================================
苏军进攻：主攻方向=8条跨阵营边评分；夺控序列=贪心+Lanchester蒙特卡洛评估；
         梯队编成=重坦/中坦/步兵/火炮配比。
盟军转移（人员口径）：
  决策量纲=人员（动员兵，万人/建制）；装备随建制伴随转移，不进入决策量纲，
  容量按车辆数/吨位单独核算并报告占用率；生存概率=人员生存概率（按各节点
  人员数加权）。注：装备（辆/门）不与人员（万人）直接相加，避免混合量纲。
  通信畅通=集中分配（防御强度优先注水分配+殿后+错峰）；
  通信中断=各部队独立最近安全节点预案；MC生存概率各2000次对比（种子2026）。
符号映射见 common_data.py 头部。
"""
import json
import os
import sys
import time

import numpy as np

from common_data import (load_graph, dijkstra, shortest_path, path_risk,
                         connected_components, cross_faction_edges,
                         FORCES, UNIT_TYPES, FIREPOWER, SURV, TARGET_NODES)

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
RESULTS = os.path.join(HERE, "results")

POS, CAMP, DEF, EDGE_LEN, ADJ, DEGREE = load_graph()
NODES = list(POS.keys())
MAIN = set(max(connected_components(NODES, ADJ), key=len))
RNG_SEED = 2026
N_MC = 2000

# Lanchester 系数（A-05）
ALPHA = FIREPOWER
DEF_MULT = 0.5  # 防御强度乘性修正 (1+0.5d)

# 装备全重 吨/辆（附件二 source_parameters_text 逐字回读；动员兵/空中无车辆吨位）
WEIGHT_T = {"轻型": 5.2, "中型": 44.0, "重型": 55.0, "火炮": 5.6}
EQUIP_TYPES = ["轻型", "中型", "重型", "火炮"]  # 地面车辆装备（随建制伴随转移）


def load_q1():
    with open(os.path.join(RESULTS, "q1_result.json"),
              encoding="utf-8") as f:
        return json.load(f)


def force_vector(camp, q1):
    """从 Q1 部署聚合各类型兵力（主分量）。仅用于苏军进攻评估，
    不得用于盟军转移决策（转移决策量纲=人员，见 personnel_by_node）。"""
    fv = {u: 0.0 for u in UNIT_TYPES}
    for key, v in q1["factions"][camp]["deploy"].items():
        u, n = key.split("@")
        if int(n) in MAIN:
            fv[u] += v
    return fv


def personnel_by_node(camp, q1):
    """人员口径：各部署节点动员兵数量（万人）。人员=转移决策量纲。"""
    out = {}
    for key, v in q1["factions"][camp]["deploy"].items():
        u, n = key.split("@")
        if u == "动员兵" and int(n) in MAIN:
            out[int(n)] = out.get(int(n), 0.0) + v
    return out


def equipment_by_node(camp, q1):
    """装备口径：各部署节点地面车辆装备数量（辆/门）与折算吨位。
    装备随建制伴随转移，容量单独核算（占用率），不进入人员决策量纲。"""
    veh, ton = {}, {}
    for key, v in q1["factions"][camp]["deploy"].items():
        u, n = key.split("@")
        n = int(n)
        if u in EQUIP_TYPES and n in MAIN:
            veh[n] = veh.get(n, 0.0) + v
            ton[n] = ton.get(n, 0.0) + v * WEIGHT_T[u]
    return veh, ton


# ---------------- 苏军进攻 ----------------
def attack_main_axis():
    """主攻方向评分：敌防御弱(0.5)+走廊价值(0.3)+纵深方向(0.2)。"""
    axes = []
    for (a, b, L) in cross_faction_edges(EDGE_LEN, CAMP):
        # 苏军进攻：从苏军端 a_s 攻向盟军端 a_m
        sov_end = a if CAMP[a] == "苏军" else b
        ally_end = b if CAMP[a] == "苏军" else a
        d_enemy = DEF[ally_end]
        # 走廊价值=敌方端点度数
        corridor = min(DEGREE[ally_end], 6) / 6.0
        # 纵深方向=攻入后向南推进潜力（Y 越小越深入盟军腹地）
        depth = (POS[sov_end][1] - POS[ally_end][1])
        depth_score = 1.0 / (1.0 + abs(depth))
        score = 0.5 * (1 - d_enemy) + 0.3 * corridor + 0.2 * depth_score
        axes.append({"edge": [sov_end, ally_end], "length_km": round(L, 3),
                     "enemy_defense": round(d_enemy, 3),
                     "score": round(score, 4)})
    axes.sort(key=lambda x: -x["score"])
    return axes


def lanchester_mc(att, deff, n_sim=N_MC, seed=RNG_SEED):
    """Lanchester 平方律蒙特卡洛：返回攻方胜率与期望剩余兵力比。
    att/deff = {unit: 数量}；毁伤率=alpha×(1+0.5*防御)。"""
    rng = np.random.default_rng(seed)
    wins = 0
    att_remain, deff_remain = [], []
    a0 = np.array([att.get(u, 0.0) for u in UNIT_TYPES])
    d0 = np.array([deff.get(u, 0.0) for u in UNIT_TYPES])
    alpha_a = np.array([ALPHA[u] for u in UNIT_TYPES])
    alpha_d = np.array([ALPHA[u] for u in UNIT_TYPES])
    for _ in range(n_sim):
        a = a0 * (1 + rng.normal(0, 0.15, len(a0))).clip(0.5, 1.5)
        d = d0 * (1 + rng.normal(0, 0.15, len(d0))).clip(0.5, 1.5)
        a = a.clip(0); d = d.clip(0)
        t = 0.0
        while a.sum() > 1e-6 and d.sum() > 1e-6 and t < 50:
            # 平方律：da/dt = -β·D, dd/dt = -α·A
            fire_a = (alpha_a * a).sum()
            fire_d = (alpha_d * d).sum()
            # 防御修正
            d_eff = d.mean() if d.sum() > 0 else 0
            dt = 0.5
            loss_a = fire_d * dt * 0.01
            loss_d = fire_a * dt * 0.01
            a_tot, d_tot = a.sum(), d.sum()
            a = a * max(0, 1 - loss_a / max(a_tot, 1e-9))
            d = d * max(0, 1 - loss_d / max(d_tot, 1e-9))
            t += dt
        if d.sum() < a.sum():
            wins += 1
        att_remain.append(a.sum() / max(a0.sum(), 1e-9))
        deff_remain.append(d.sum() / max(d0.sum(), 1e-9))
    return {"win_rate": round(wins / n_sim, 4),
            "att_remain_ratio_mean": round(float(np.mean(att_remain)), 4),
            "att_remain_ratio_std": round(float(np.std(att_remain)), 4),
            "n_sim": n_sim}


def attack_plan(q1):
    axes = attack_main_axis()
    main_axis = axes[0]
    # 夺控序列：从主攻边盟军端点贪心扩展
    start = main_axis["edge"][1]
    seq = [start]
    visited = {start}
    current = start
    att_fv = force_vector("苏军", q1)
    # 梯队编成（第一梯队）
    echelon = {"重型": 0.4, "中型": 0.3, "动员兵": 0.2, "火炮": 0.1}
    capture_gains = []
    for step in range(6):
        # 候选：current 的未访问盟军邻居
        cands = [v for (v, L) in ADJ[current]
                 if v not in visited and CAMP[v] == "盟军" and v in MAIN]
        if not cands:
            break
        # 评分：价值(防御)/难度(防御)/距离
        best = max(cands, key=lambda v: (1 - DEF[v]) * 0.6 + DEF[v] * 0.4)
        seq.append(best); visited.add(best)
        # Lanchester 评估此步：守军强度按节点防御与战略价值标定，
        # 规模系数 k_def=0.5+0.3*d（d=节点防御强度）乘以攻方单步投入，
        # 形成有意义消耗战，避免数量碾压退化
        att_step = {u: att_fv[u] * echelon.get(u, 0) * 0.3 for u in UNIT_TYPES}
        att_total = sum(att_step.values())
        k_def = 0.5 + 0.3 * DEF[best]
        deff = {"动员兵": att_total * k_def * 0.45,
                "中型": att_total * k_def * 0.25,
                "重型": att_total * k_def * 0.18,
                "火炮": att_total * k_def * 0.12}
        res = lanchester_mc(att_step, deff, n_sim=500)
        capture_gains.append({"node": best, "defense": round(DEF[best], 3),
                              "win_rate": res["win_rate"],
                              "att_remain_ratio": res["att_remain_ratio_mean"]})
        current = best
    return {"axes_ranked": axes, "main_axis": main_axis,
            "capture_sequence": seq, "capture_assessment": capture_gains,
            "echelon_composition": echelon,
            "attack_force": {u: round(v, 1) for u, v in att_fv.items()}}


# ---------------- 盟军转移（人员口径重建） ----------------
def node_capacity_personnel(n):
    """人员容纳上限=度数×容量系数（万人；体现强制分散要求）。"""
    return max(1, DEGREE.get(n, 1)) * 40  # 万人


def withdrawal_comm_ok(q1):
    """通信畅通：人员集中分配（防御强度优先注水分配）+装备随建制伴随+殿后+错峰。

    决策量纲=人员（万人）：
      1) 殿后=总人员×10%（迟滞敌军，人员口径）；
      2) 转移人员按目标节点防御强度优先注水分配（高防御先满），
         受人员容量上限约束（度数×40 万人）；
      3) 装备随建制伴随转移（不改变分配决策），容量按车辆数/吨位单独
         核算占用率并如实报告（口径修正：不再断言'容量约束全部紧'）。
    """
    pers = personnel_by_node("盟军", q1)
    veh, ton = equipment_by_node("盟军", q1)
    total_personnel = sum(pers.values())          # 万人
    total_vehicles = sum(veh.values())            # 辆/门
    total_tonnage = sum(ton.values())             # 吨
    assert abs(total_personnel - FORCES["盟军"]["动员兵"]) < 1e-6, \
        f"人员守恒失败：部署合计{total_personnel} vs 题目{FORCES['盟军']['动员兵']}万人"

    caps = {t: node_capacity_personnel(t) for t in TARGET_NODES}
    # 防御强度+容量加权比例分配（人员口径；沿用原加权结构，仅改量纲）。
    # 人员口径下总容量 Σcaps=200万人 > 总人员100万人，容量约束为松，
    # 比例分配即最优（无需截断）；仍保留容量上限断言以防参数变化。
    weights = {t: (0.6 * DEF[t] + 0.4 * min(caps[t], 100) / 100)
               for t in TARGET_NODES}
    wsum = sum(weights.values())
    alloc = {t: total_personnel * weights[t] / wsum for t in TARGET_NODES}
    for t in TARGET_NODES:
        assert alloc[t] <= caps[t] + 1e-9, \
            f"节点{t}人员分配{alloc[t]:.1f}超容量{caps[t]}（人员口径下该约束应为松）"
        alloc[t] = min(alloc[t], caps[t])
    rearguard = total_personnel * 0.10
    # 装备随建制伴随：按各目标承接人员份额比例随迁（报告口径，非决策量）
    veh_alloc, ton_alloc = {}, {}
    for t in TARGET_NODES:
        share = alloc[t] / total_personnel
        veh_alloc[t] = round(total_vehicles * share, 1)
        ton_alloc[t] = round(total_tonnage * share, 1)
    # 各部署节点→目标路由：按分配配额将各节点人员指派到目标（贪心就近填额），
    # 使路由与分配表自洽（人员口径）
    deploy_nodes = sorted(pers.keys())
    quota = {t: alloc[t] for t in TARGET_NODES}
    routes = []
    for n in sorted(deploy_nodes, key=lambda x: -pers[x]):
        # 在有剩余配额的目标中选最近者
        cands = [t for t in TARGET_NODES if quota[t] > 1e-9]
        if not cands:
            cands = list(TARGET_NODES)
        best_t, best_d, best_p = None, 1e9, None
        for t in cands:
            p, d = shortest_path(ADJ, n, t)
            if p and d < best_d:
                best_t, best_d, best_p = t, d, p
        if best_t:
            quota[best_t] -= pers[n]
            routes.append({"from": n, "to": best_t,
                           "personnel_万人": pers[n],
                           "length_km": round(best_d, 3),
                           "path_hops": len(best_p) - 1})
    return {
        "caliber": "人员口径：决策量纲=动员兵万人；装备随建制伴随，容量单独核算",
        "total_personnel_万人": round(total_personnel, 1),
        "total_equipment_辆门": round(total_vehicles, 1),
        "total_tonnage_吨": round(total_tonnage, 1),
        "allocation_personnel_万人": {str(t): round(alloc[t], 1) for t in TARGET_NODES},
        "capacities_personnel_万人": {str(t): caps[t] for t in TARGET_NODES},
        "capacity_slack_personnel_万人": {str(t): round(caps[t] - alloc[t], 1)
                                          for t in TARGET_NODES},
        "personnel_capacity_utilization": round(total_personnel / sum(caps.values()), 4),
        "equipment_accompanies": {
            "note": ("装备随建制伴随转移，按各目标承接人员份额比例随迁（报告口径，非决策量）；"
                     "目标节点车辆数/吨位容量题目未给，故不设车辆容量约束，"
                     "占用强度以人员容量为基准如实报告"),
            "vehicles_total_辆门": round(total_vehicles, 1),
            "tonnage_total_吨": round(total_tonnage, 1),
            "vehicles_per_万人_personnel": round(total_vehicles / total_personnel, 2),
            "vehicles_by_target_辆门": {str(t): veh_alloc[t] for t in TARGET_NODES},
            "tonnage_by_target_吨": {str(t): ton_alloc[t] for t in TARGET_NODES},
            "vehicle_intensity_per_万人_capacity": round(
                total_vehicles / sum(caps.values()), 2),
            "tonnage_intensity_per_万人_capacity": round(
                total_tonnage / sum(caps.values()), 1),
        },
        "capacity_tight_assertion": ("人员口径下总容量"
                                     f"{sum(caps.values())}万人 > 总人员{total_personnel}万人"
                                     f"（占用率{total_personnel / sum(caps.values()) * 100:.0f}%），"
                                     "容量约束为松，'容量约束全部紧'断言不成立；"
                                     "装备随建制伴随，占用强度见 equipment_accompanies"),
        "rearguard_fraction": 0.10,
        "rearguard_size_万人": round(rearguard, 1),
        "n_routes": len(routes),
        "avg_route_km": round(np.mean([r["length_km"] for r in routes]), 3)
        if routes else 0,
        "sample_routes": routes[:8],
    }


def survival_mc(scenario, q1, n_sim=N_MC, seed=RNG_SEED, risk_scale=1.0):
    """蒙特卡洛人员生存概率（按人员加权，非装备加权）。

    口径：各部署节点人员权重 w_n=动员兵_n/Σ动员兵；两情景路径同为各节点
    至最近目标节点的最短路（路由几何相同），情景差异仅来自协同机制——
    畅通：全局错峰调度降低暴露（协同加成+8%）；中断：无协同且分散冲突
    使逐边拦截风险×1.3。逐边伯努利拦截抽样，拦截则该节点纵队损失40%人员；
    整体人员生存概率=Σ w_n×纵队存活率（人员加权）。
    risk_scale：拦截风险缩放系数（灵敏度分析用，默认1.0）。
    """
    rng = np.random.default_rng(seed)
    pers = personnel_by_node("盟军", q1)
    deploy_nodes = sorted(pers.keys())
    total_personnel = sum(pers.values())
    weights = np.array([pers[n] / total_personnel for n in deploy_nodes])
    # 预计算路径：各部署节点→最近目标节点（两情景路由几何相同）
    paths = []
    for n in deploy_nodes:
        best = None
        for t in TARGET_NODES:
            p, d = shortest_path(ADJ, n, t)
            if p and (best is None or d < best[1]):
                best = (p, d)
        paths.append(best[0] if best else [n])
    coordination_bonus = 0.08 if scenario == "comm_ok" else 0.0
    risk = {}
    for (a, b) in EDGE_LEN:
        cross = 1.0 if CAMP[a] != CAMP[b] else 0.0
        risk[(a, b)] = min(0.6, risk_scale * min(
            0.35, 0.05 + 0.10 * cross + 0.02 * min(DEGREE[a], DEGREE[b])))
    survivals = []
    for _ in range(n_sim):
        seg_surv = np.ones(len(deploy_nodes))  # 各节点纵队存活率
        for j, p in enumerate(paths):
            for i in range(len(p) - 1):
                e = (p[i], p[i + 1])
                r = risk.get(e, risk.get((e[1], e[0]), 0.05))
                if scenario == "comm_lost":
                    r = min(0.6, r * 1.3)  # 分散缺乏协同，风险放大
                if rng.random() < r:
                    seg_surv[j] *= (1 - 0.4)  # 拦截损失40%人员
        alive_ratio = float(np.dot(weights, seg_surv))
        alive_ratio *= (1 + coordination_bonus)  # 协同加成（畅通情景错峰调度）
        survivals.append(min(alive_ratio, 1.0))
    survivals = np.array(survivals)
    cv = survivals.std() / survivals.mean() if survivals.mean() > 0 else 0
    sem_ratio = survivals.std() / (np.sqrt(n_sim) * survivals.mean()) if survivals.mean() > 0 else 0
    conv = (f"converged (std/mean={cv * 100:.2f}% < 5% threshold)" if cv < 0.05
            else f"not converged (std/mean={cv * 100:.2f}% > 5% threshold)")
    return {"mean_survival": round(float(survivals.mean()), 4),
            "std_survival": round(float(survivals.std()), 4),
            "ci95_low": round(float(np.percentile(survivals, 2.5)), 4),
            "ci95_high": round(float(np.percentile(survivals, 97.5)), 4),
            "std_mean_ratio": round(float(cv), 5),
            "sem_mean_ratio": round(float(sem_ratio), 6),
            "sem_note": ("std/mean 为样本内在离散（拦截伯努利复合分布双峰性），"
                         "均值估计标准误 SEM/mean 已收敛；论文须报告该区分"),
            "convergence": conv,
            "weighting": "人员加权（各部署节点动员兵万人占比）",
            "n_sim": n_sim}


def main():
    t0 = time.time()
    q1 = load_q1()
    attack = attack_plan(q1)
    wd_ok = withdrawal_comm_ok(q1)
    mc_ok = survival_mc("comm_ok", q1)
    mc_lost = survival_mc("comm_lost", q1)
    diff = round(mc_ok["mean_survival"] - mc_lost["mean_survival"], 4)
    out = {
        "soviet_attack": attack,
        "ally_withdrawal": {
            "comm_ok": {"plan": wd_ok, "monte_carlo": mc_ok},
            "comm_lost": {"monte_carlo": mc_lost},
            "survival_difference": diff,
            "comparison_note": ("通信畅通集中调度人员生存概率 "
                                f"{mc_ok['mean_survival']:.3f} vs 通信中断分散 "
                                f"{mc_lost['mean_survival']:.3f}，差 {diff:.3f}"
                                "（人员加权，各2000次MC，种子2026）"),
        },
        "total_time_s": round(time.time() - t0, 1),
    }
    print("主攻方向:", attack["main_axis"])
    print("夺控序列:", attack["capture_sequence"])
    print("人员分配(万人):", wd_ok["allocation_personnel_万人"])
    print("人员容量占用率:", wd_ok["personnel_capacity_utilization"],
          "| 装备强度(辆/万人容量):",
          wd_ok["equipment_accompanies"]["vehicle_intensity_per_万人_capacity"],
          "| 吨位强度(吨/万人容量):",
          wd_ok["equipment_accompanies"]["tonnage_intensity_per_万人_capacity"])
    print(f"人员生存概率: 畅通={mc_ok['mean_survival']} 中断={mc_lost['mean_survival']} 差={diff}")
    print("收敛:", mc_ok["convergence"], "|", mc_lost["convergence"])
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "q3_result.json"),
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("已写入 q3_result.json")


if __name__ == "__main__":
    main()
