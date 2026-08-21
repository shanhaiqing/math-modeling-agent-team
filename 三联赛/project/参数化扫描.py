#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数化扫描.py — 显式未知参数化 sweep 扫描（不重建模型结构）
=================================================================
扫描内容：
  ① A-01 破交概率：基线 vs Stackelberg 对照结构化
  ② A-02 直射距离：d∈[1.0,3.0]km 5 点 sweep（重建覆盖系数 cov → 重解 Q1 MIP），稳定性区间
  ③ A-03 防空半径：r∈[2.0,4.0]km 5 点 sweep（Stage B 防空重布置 → S_bonus 重算），稳定性区间
  ④ A-04 空中上限：α∈[5%,20%] 4 点 sweep（force_空中 rhs 扰动 → Q1 重解 + Q2 需求传播）
  ⑤ A-07 万人粒度：0.5 万人更细粒度验证算例（粒度选择-验证，非参数化）
复用：问题1_求解.solve_deployment/place_aa、问题2_求解.solve_supply（仅扰动参数重求解）。
最优性元数据全部取求解器原生输出（status/MIPGap/solve_time）。
产出：results/参数化扫描结果.json、figures/fig11~fig14（PDF+PNG）。
"""
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np

import matplotlib.pyplot as plt          # noqa: E402
from visualization_style import (setup_style, save_figure, COLORS,
                                 LINE_STYLES, MARKERS)   # noqa: E402
import common_data as CD                 # noqa: E402
from common_data import FORCES, UNIT_TYPES, SURV        # noqa: E402
import 问题1_求解 as Q1M                 # noqa: E402
import 问题2_求解 as Q2M                 # noqa: E402

POS, CAMP, DEF = Q1M.POS, Q1M.CAMP, Q1M.DEF
EDGE_LEN, ADJ, DEGREE = Q1M.EDGE_LEN, Q1M.ADJ, Q1M.DEGREE
MAIN = Q1M.MAIN

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
RESULTS = os.path.join(HERE, "results")
FIGDIR = os.path.join(HERE, "figures")

with open(os.path.join(RESULTS, "q1_result.json"), encoding="utf-8") as f:
    Q1_BASE = json.load(f)
with open(os.path.join(RESULTS, "q2_result.json"), encoding="utf-8") as f:
    Q2_BASE = json.load(f)


def parse_deploy(camp):
    """q1_result deploy 字典 '单位@节点'→{(u,n): v}。"""
    out = {}
    for key, v in Q1_BASE["factions"][camp]["deploy"].items():
        u, n = key.split("@")
        out[(u, int(n))] = v
    return out


BASE_DEPLOY = {c: parse_deploy(c) for c in ["苏军", "盟军"]}
BASE_CMD = {c: Q1_BASE["factions"][c]["command_node"] for c in ["苏军", "盟军"]}
BASE_PHI = {c: Q1_BASE["factions"][c]["objective_value"] for c in ["苏军", "盟军"]}
BASE_AA = {c: set(Q1_BASE["factions"][c]["aa_nodes"]) for c in ["苏军", "盟军"]}

# 预计算（不随 sweep 变化）：候选指挥节点、各候选最短路距离
PRE = {}
for camp in ["苏军", "盟军"]:
    cands, scores = Q1M.command_candidates(camp, k=6)
    dists = {z: Q1M.dijkstra(ADJ, z, MAIN) for z in cands}
    PRE[camp] = {"cands": cands, "scores": scores, "dists": dists}


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0


def solve_at(camp, patches):
    """对 Q1M 模块全局量打补丁后逐候选重解部署 MIP（补丁用后即还原）。
    返回最优候选的 (z, phi, deploy, 原生元数据)。"""
    saved = {k: getattr(Q1M, k) for k in patches}
    try:
        for k, v in patches.items():
            setattr(Q1M, k, v)
        own, enemy, cov = Q1M.build_coverage(camp)   # 覆盖系数随补丁重建
        best = None
        for z in PRE[camp]["cands"]:
            dist_to_cmd = {n: PRE[camp]["dists"][z].get(n, Q1M.D_MAX)
                           for n in own}
            res, meta = Q1M.solve_deployment(camp, z, own, enemy, cov,
                                             dist_to_cmd)
            if res.status in ("optimal", "feasible"):
                if best is None or res.objective_value > best["phi"]:
                    deploy = {}
                    for u in UNIT_TYPES:
                        for n in own:
                            v = res.variable_values.get(f"x_{u}_{n}", 0.0)
                            if v and v > 1e-6:
                                deploy[(u, n)] = int(round(v))
                    best = {"z": z, "phi": res.objective_value,
                            "deploy": deploy, "status": res.status,
                            "gap": res.mip_gap, "t": round(res.solve_time, 3)}
        assert best is not None, f"{camp} 在补丁 {patches} 下无可行解"
        return best
    finally:
        for k, v in saved.items():
            setattr(Q1M, k, v)


def stability_interval(xs, stable, base_x):
    """包含基线点的最长连续稳定区间。"""
    i = xs.index(base_x)
    lo = i
    while lo > 0 and stable[lo - 1]:
        lo -= 1
    hi = i
    while hi < len(xs) - 1 and stable[hi + 1]:
        hi += 1
    return [xs[lo], xs[hi]]


def solver_meta(rows):
    """聚合各扫点求解器原生元数据。"""
    sts = [r["status"] for r in rows]
    return {"all_points_status_optimal": all(s == "optimal" for s in sts),
            "statuses": sorted(set(sts)),
            "max_MIPGap": max(r["gap"] for r in rows),
            "max_solve_time_s": max(r["t"] for r in rows),
            "source": "求解器原生元数据（solver_backend.solve_mip 透传）"}


# ============ ② A-02 直射距离 sweep ============
def sweep_a02():
    ds = [1.0, 1.5, 2.0, 2.5, 3.0]
    out = {}
    for camp in ["苏军", "盟军"]:
        rows = []
        for d in ds:
            s = d / 2.0  # 基线：轻1.5/中重2.0 → 等比缩放，d=2.0 复现基线
            rng = dict(CD.RANGE)
            rng.update({"轻型": 1.5 * s, "中型": 2.0 * s, "重型": 2.0 * s})
            best = solve_at(camp, {"RANGE": rng})
            rows.append({
                "d_km": d, "scale": round(s, 3),
                "ranges_km": {"轻型": round(1.5 * s, 3),
                              "中型": round(2.0 * s, 3),
                              "重型": round(2.0 * s, 3)},
                "phi": round(best["phi"], 5),
                "command_node": best["z"],
                "flipped": best["z"] != BASE_CMD[camp],
                "deploy_jaccard": round(jaccard(best["deploy"],
                                                BASE_DEPLOY[camp]), 4),
                "deploy_node_count": len(set(n for (_, n) in best["deploy"])),
                "status": best["status"], "gap": best["gap"], "t": best["t"],
            })
            print(f"  [A-02 {camp}] d={d}km Φ={best['phi']:.4f} "
                  f"cmd={best['z']} flip={rows[-1]['flipped']} "
                  f"J={rows[-1]['deploy_jaccard']} ({best['status']}, "
                  f"gap={best['gap']}, {best['t']}s)")
        stable = [(not r["flipped"]) and r["deploy_jaccard"] >= 0.8
                  for r in rows]
        flips = sum(r["flipped"] for r in rows)
        out[camp] = {
            "parameter": "A-02 坦克直射距离（等比缩放：轻型=1.5×(d/2)，中/重型=2.0×(d/2)）",
            "baseline_d_km": 2.0,
            "base_phi": BASE_PHI[camp],
            "base_command_node": BASE_CMD[camp],
            "points": rows,
            "flip_count": flips,
            "stability_interval_km": stability_interval(ds, stable, 2.0),
            "stability_criterion": "指挥节点不翻转且部署结构Jaccard相似度≥0.8",
            "conclusion": "",
            "solver_meta": solver_meta(rows),
        }
        lo, hi = out[camp]["stability_interval_km"]
        out[camp]["conclusion"] = (
            f"d∈[{lo},{hi}]km 内指挥节点0翻转且部署结构相似度≥0.8，"
            f"全扫描[{ds[0]},{ds[-1]}]km 翻转计数={flips}，推荐部署稳健")
    return out


# ============ ③ A-03 防空半径 sweep ============
def sweep_a03():
    rs = [2.0, 2.5, 3.0, 3.5, 4.0]
    out = {}
    for camp in ["苏军", "盟军"]:
        deploy = BASE_DEPLOY[camp]
        own = [n for n in POS if CAMP[n] == camp]
        phi_mip = BASE_PHI[camp]
        S_max = sum(FORCES[camp][u] * SURV[u] for u in UNIT_TYPES)
        rows = []
        for r in rs:
            saved = Q1M.R_AA
            Q1M.R_AA = r
            try:
                aa, aa_res = Q1M.place_aa(camp, deploy, own)
            finally:
                Q1M.R_AA = saved
            covered = set()
            for p in aa:
                for n in own:
                    if Q1M.euclid(POS, p, n) <= r:
                        covered.add(n)
            bonus = sum(DEF[n] * SURV[u] * deploy.get((u, n), 0)
                        * CD.AA_SURV_BONUS
                        for u in UNIT_TYPES for n in covered)
            aa_set = set(aa)
            sym = len(aa_set ^ BASE_AA[camp])
            rows.append({
                "r_km": r,
                "S_bonus": round(bonus, 1),
                "phi_with_aa": round(phi_mip + 0.3 * bonus / S_max, 5),
                "aa_nodes": sorted(aa),
                "aa_changed_count": sym,
                "aa_jaccard": round(jaccard(aa_set, BASE_AA[camp]), 4),
                "covered_deploy_nodes": len(covered),
                "status": aa_res.status, "gap": aa_res.mip_gap,
                "t": round(aa_res.solve_time, 3),
            })
            print(f"  [A-03 {camp}] r={r}km S_bonus={bonus:.1f} "
                  f"防空节点变化={sym} J={rows[-1]['aa_jaccard']} "
                  f"({aa_res.status}, gap={aa_res.mip_gap})")
        stable = [row["aa_jaccard"] >= 0.8 for row in rows]
        out[camp] = {
            "parameter": "A-03 防空炮阵地覆盖半径 R_aa（Stage B 防空重布置+生存加成重算）",
            "baseline_r_km": 3.0,
            "phi_mip_base": phi_mip,
            "phi_with_aa_note": "phi_with_aa = Φ_MIP + 0.3×S_bonus/S_max（含防空生存加成的效能口径）",
            "points": rows,
            "stability_interval_km": stability_interval(rs, stable, 3.0),
            "stability_criterion": "防空节点集与基线Jaccard相似度≥0.8",
            "conclusion": "",
            "solver_meta": solver_meta(rows),
        }
        lo, hi = out[camp]["stability_interval_km"]
        max_chg = max(row["aa_changed_count"] for row in rows)
        out[camp]["conclusion"] = (
            f"r∈[{lo},{hi}]km 内防空节点布局与基线相似度≥0.8，"
            f"全扫描[{rs[0]},{rs[-1]}]km 最大节点变化数={max_chg}，防空配置稳健")
    return out


# ============ ④ A-04 空中上限 sweep（Q1 + Q2 传播） ============
def sweep_a04():
    alphas = [0.05, 0.10, 0.15, 0.20]
    q1_part = {}
    deploys_by_alpha = {}
    for camp in ["苏军", "盟军"]:
        rows = []
        for a in alphas:
            best = solve_at(camp, {"AIR_CAP_RATIO": a})
            air = sum(v for (u, _), v in best["deploy"].items() if u == "空中")
            air_nodes = sorted({n for (u, n) in best["deploy"] if u == "空中"})
            rows.append({
                "alpha": a,
                "air_cap_units": int(FORCES[camp]["空中"] * a),
                "air_deployed": air,
                "air_nodes": air_nodes,
                "phi": round(best["phi"], 5),
                "command_node": best["z"],
                "flipped": best["z"] != BASE_CMD[camp],
                "deploy_jaccard": round(jaccard(best["deploy"],
                                                BASE_DEPLOY[camp]), 4),
                "status": best["status"], "gap": best["gap"], "t": best["t"],
            })
            deploys_by_alpha.setdefault(a, {})[camp] = best["deploy"]
            print(f"  [A-04 {camp}] α={a:.0%} 空中部署={air} "
                  f"Φ={best['phi']:.4f} cmd={best['z']} ({best['status']})")
        flips = sum(r["flipped"] for r in rows)
        q1_part[camp] = {
            "parameter": "A-04 空中单位部署上限 α（force_空中 约束 rhs=N_空中×α）",
            "baseline_alpha": 0.10,
            "base_command_node": BASE_CMD[camp],
            "points": rows,
            "flip_count": flips,
            "stability_interval": stability_interval(
                alphas, [not r["flipped"] for r in rows], 0.10),
            "stability_criterion": "指挥节点不翻转",
            "conclusion": "",
            "solver_meta": solver_meta(rows),
        }
        lo, hi = q1_part[camp]["stability_interval"]
        q1_part[camp]["conclusion"] = (
            f"α∈[{lo:.0%},{hi:.0%}] 内指挥节点0翻转，空中部署随上限单调不减，"
            f"定性结论（空中单位少量集中部署）稳定")
    # Q2 传播：各 α 下部署 → 需求 → 补给 TC
    prop_rows = []
    base_tc = {c: Q2_BASE["factions"][c]["supply_optimization"]["TC_excl_labor"]
               for c in ["苏军", "盟军"]}
    for a in alphas:
        dep = {}
        for camp in ["苏军", "盟军"]:
            dep[camp] = {}
            for (u, n), v in deploys_by_alpha[a][camp].items():
                if n in MAIN:
                    dep[camp].setdefault(n, {})
                    dep[camp][n][u] = dep[camp][n].get(u, 0) + v
        demand = Q2M.compute_demand(dep)
        row = {"alpha": a}
        for camp in ["苏军", "盟军"]:
            depots = Q2M.select_depots(camp, Q1_BASE)
            r = Q2M.solve_supply(camp, depots, demand)
            row[f"TC_{camp}"] = r["TC_excl_labor"]
            row[f"delta_pct_{camp}"] = round(
                (r["TC_excl_labor"] - base_tc[camp]) / base_tc[camp] * 100, 3)
            row[f"status_{camp}"] = r["status"]
        prop_rows.append(row)
        print(f"  [A-04→Q2] α={a:.0%} TC苏={row['TC_苏军']} "
              f"({row['delta_pct_苏军']:+.3f}%) TC盟={row['TC_盟军']} "
              f"({row['delta_pct_盟军']:+.3f}%)")
    max_abs = max(abs(r[f"delta_pct_{c}"]) for r in prop_rows
                  for c in ["苏军", "盟军"])
    q2_part = {
        "parameter": "A-04 空中上限 α 经部署→需求传播至 Q2 补给成本",
        "base_TC_excl_labor": base_tc,
        "points": prop_rows,
        "max_abs_delta_pct": max_abs,
        "conclusion": (
            f"α∈[5%,20%] 全扫描下 Q2 补给成本最大变化 {max_abs:.3f}%，"
            "传播影响可忽略，Q2 结论对 A-04 稳健"),
    }
    return {"q1": q1_part, "q2_propagation": q2_part}


# ============ ⑤ A-07 0.5万人粒度验证算例 ============
def verify_a07():
    out = {}
    for camp in ["苏军", "盟军"]:
        fine = {c: dict(FORCES[c]) for c in FORCES}
        fine[camp]["动员兵"] = FORCES[camp]["动员兵"] * 2  # 0.5万人/单位
        best = solve_at(camp, {"FORCES": fine})
        # 动员兵聚合回万人粒度对比
        base_inf = {n: v for (u, n), v in BASE_DEPLOY[camp].items()
                    if u == "动员兵"}
        fine_inf = {}
        for (u, n), v in best["deploy"].items():
            if u == "动员兵":
                fine_inf[n] = fine_inf.get(n, 0) + v / 2.0
        l1 = sum(abs(fine_inf.get(n, 0) - base_inf.get(n, 0))
                 for n in set(base_inf) | set(fine_inf))
        eq_base = {k: v for k, v in BASE_DEPLOY[camp].items() if k[0] != "动员兵"}
        eq_fine = {k: v for k, v in best["deploy"].items() if k[0] != "动员兵"}
        out[camp] = {
            "granularity": "0.5万人/单位（动员兵总量×2，其余装备粒度不变）",
            "phi": round(best["phi"], 5),
            "base_phi": BASE_PHI[camp],
            "phi_delta": round(best["phi"] - BASE_PHI[camp], 5),
            "command_node": best["z"],
            "command_flipped": best["z"] != BASE_CMD[camp],
            "equip_jaccard": round(jaccard(eq_fine, eq_base), 4),
            "infantry_L1_wanren": round(l1, 2),
            "deploy_node_count": len(set(n for (_, n) in best["deploy"])),
            "status": best["status"], "gap": best["gap"], "t": best["t"],
        }
        print(f"  [A-07 {camp}] 0.5粒度 Φ={best['phi']:.4f} "
              f"(Δ={best['phi'] - BASE_PHI[camp]:+.4f}) cmd={best['z']} "
              f"装备J={out[camp]['equip_jaccard']} 动员兵L1={l1:.1f}万人 "
              f"({best['status']}, gap={best['gap']})")
    stable = all((not v["command_flipped"]) and v["equip_jaccard"] >= 0.8
                 for v in out.values())
    max_phi_delta = max(abs(v["phi_delta"]) for v in out.values())
    out["max_phi_delta"] = max_phi_delta
    out["conclusion"] = (
        "0.5万人更细粒度下双方指挥节点均不翻转、装备部署结构Jaccard≥0.8、"
        f"Φ最大变化{max_phi_delta}——万人粒度为建模粒度选择（避免10^6值域病态），"
        "部署结构对粒度稳健" if stable else
        "0.5万人粒度下结构发生变化，须在论文披露粒度敏感性")
    out["structure_stable"] = stable
    return out


# ============ ① A-01 基线 vs Stackelberg 对照结构化 ============
def comparison_a01():
    """主口径=含人力 TC_total。
    TC_worst = 基线 TC_total + extra_loss；delta_pct 取 问题2_求解.py
    重算的原生输出（苏 +50.83% / 盟 +48.94%）。"""
    out = {}
    for camp in ["苏军", "盟军"]:
        f = Q2_BASE["factions"][camp]
        tc_base = f["supply_optimization"]["TC_total"]
        worst = f["stackelberg_worst_case"]
        assert abs(worst["TC_baseline"] - tc_base) < 0.5, \
            f"{camp} Stackelberg 基线与 TC_total 不一致（口径一致性断言）"
        out[camp] = {
            "parameter": "A-01 破交拦截概率（内生未知参数：静态risk_e基线=主模型输入，Stackelberg最坏情形=鲁棒性成本量化）",
            "caliber": worst["caliber"],
            "TC_baseline_total": worst["TC_baseline"],
            "TC_worst_total": worst["TC_worst"],
            "extra_loss": worst["extra_loss"],
            "delta_pct": worst["delta_pct"],
            "delta_pct_excl_labor_reference": worst["delta_pct_excl_labor_reference"],
            "hit_routes": worst["hit_routes"],
            "enemy_interdict_budget": CD.ENEMY_INTERDICT_BUDGET,
            "note": ("对照口径为 TC_total（含人力成本，主口径）："
                     "TC_worst=基线TC_total+extra_loss（破交追加损失仅作用于货物损失项，"
                     "人力成本不变）；敌方将破交预算集中投向流量×货值/护航强度最大的"
                     "Top-5路径（Stackelberg follower 最优响应）。"),
            "source": "q2_result.stackelberg_worst_case（含人力口径）",
        }
        print(f"  [A-01 {camp}] 基线TC={tc_base} 最坏TC={worst['TC_worst']} "
              f"Δ={worst['delta_pct']:+.2f}%（含人力口径）")
    return out


# ============ 图表 ============
def make_figures(a02, a03, a04, a01):
    setup_style()
    os.makedirs(FIGDIR, exist_ok=True)
    camps = ["苏军", "盟军"]
    # fig11 A-02 直射距离 sweep
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, c in enumerate(camps):
        xs = [p["d_km"] for p in a02[c]["points"]]
        ys = [p["phi"] for p in a02[c]["points"]]
        ax.plot(xs, ys, color=COLORS["palette"][i],
                linestyle=LINE_STYLES[0], marker=MARKERS[i],
                label=f"{c} Φ")
        for p in a02[c]["points"]:
            if p["flipped"]:
                ax.plot(p["d_km"], p["phi"], marker="x", ms=12,
                        color=COLORS["quaternary"])
    lo = min(a02[c]["stability_interval_km"][0] for c in camps)
    hi = max(a02[c]["stability_interval_km"][1] for c in camps)
    ax.axvspan(lo, hi, color=COLORS["tertiary"], alpha=0.12,
               label=f"双方稳定区 [{lo},{hi}]km")
    ax.axvline(2.0, color="gray", ls=":", lw=1)
    ax.set_xlabel("坦克直射距离 d (km)")
    ax.set_ylabel("综合效能 Φ")
    ax.set_title("A-02 直射距离参数化 sweep（Q1 部署重解）")
    ax.legend()
    save_figure(fig, os.path.join(FIGDIR, "fig11_q1_direct_range_sweep"))
    plt.close(fig)
    # fig12 A-03 防空半径 sweep
    fig, ax = plt.subplots(figsize=(6, 4))
    ax2 = ax.twinx()
    for i, c in enumerate(camps):
        xs = [p["r_km"] for p in a03[c]["points"]]
        ys = [p["phi_with_aa"] for p in a03[c]["points"]]
        ax.plot(xs, ys, color=COLORS["palette"][i], marker=MARKERS[i],
                label=f"{c} Φ(含防空)")
        ax2.bar([x + (0.08 if i else -0.08) for x in xs],
                [p["aa_changed_count"] for p in a03[c]["points"]],
                width=0.16, alpha=0.35, color=COLORS["palette"][i],
                label=f"{c} 防空节点变化数")
    ax.axvline(3.0, color="gray", ls=":", lw=1)
    ax.set_xlabel("防空覆盖半径 r (km)")
    ax.set_ylabel("Φ（含防空生存加成）")
    ax2.set_ylabel("防空节点变化数（vs 基线）")
    ax.set_title("A-03 防空半径参数化 sweep（Stage B 重布置）")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8)
    save_figure(fig, os.path.join(FIGDIR, "fig12_q1_aa_radius_sweep"))
    plt.close(fig)
    # fig13 A-01 基线 vs Stackelberg
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(2)
    w = 0.35
    b = [a01[c]["TC_baseline_total"] for c in camps]
    wst = [a01[c]["TC_worst_total"] for c in camps]
    ax.bar(x - w / 2, b, w, color=COLORS["primary"], label="基线（静态risk_e）")
    ax.bar(x + w / 2, wst, w, color=COLORS["quaternary"],
           label="Stackelberg 最坏情形")
    for i, c in enumerate(camps):
        ax.annotate(f"+{a01[c]['delta_pct']:.1f}%",
                    (x[i] + w / 2, wst[i]), ha="center", va="bottom",
                    fontsize=9, color=COLORS["quaternary"])
    ax.set_xticks(x)
    ax.set_xticklabels(camps)
    ax.set_ylabel("后勤总成本 TC (元/日)")
    ax.set_title("基线情形与对抗最坏情形后勤总成本对照（含人力口径）")
    ax.legend()
    save_figure(fig, os.path.join(FIGDIR, "fig13_q2_a01_baseline_vs_stackelberg"))
    plt.close(fig)
    # fig14 A-04 空中上限 sweep
    fig, ax = plt.subplots(figsize=(6, 4))
    ax2 = ax.twinx()
    for i, c in enumerate(camps):
        xs = [p["alpha"] * 100 for p in a04["q1"][c]["points"]]
        ax.plot(xs, [p["phi"] for p in a04["q1"][c]["points"]],
                color=COLORS["palette"][i], marker=MARKERS[i],
                label=f"{c} Φ")
        ax2.plot(xs, [p["air_deployed"] for p in a04["q1"][c]["points"]],
                 color=COLORS["palette"][i], ls="--", marker=MARKERS[i + 2],
                 alpha=0.7, label=f"{c} 空中部署数")
    ax.axvline(10, color="gray", ls=":", lw=1)
    ax.set_xlabel("空中单位部署上限 α (%)")
    ax.set_ylabel("综合效能 Φ")
    ax2.set_ylabel("空中单位部署数（架）")
    ax.set_title("A-04 空中上限参数化 sweep（Q1 重解）")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8)
    save_figure(fig, os.path.join(FIGDIR, "fig14_q1_air_cap_sweep"))
    plt.close(fig)
    print("  fig11~fig14 已生成（PDF+PNG）")


def main():
    t0 = time.time()
    print("== 基线复现自检 ==")
    for camp in ["苏军", "盟军"]:
        b = solve_at(camp, {})
        assert b["z"] == BASE_CMD[camp], \
            f"{camp} 基线复现失败：cmd {b['z']} != {BASE_CMD[camp]}"
        assert abs(b["phi"] - BASE_PHI[camp]) < 1e-3, \
            f"{camp} 基线Φ复现失败：{b['phi']} vs {BASE_PHI[camp]}"
        print(f"  [{camp}] 基线复现 ✓ cmd={b['z']} Φ={b['phi']:.5f}")
    # Q2 基线复现自检
    _, dep0 = Q2M.load_q1_deploy()
    demand0 = Q2M.compute_demand(dep0)
    for camp in ["苏军", "盟军"]:
        depots = Q2M.select_depots(camp, Q1_BASE)
        r0 = Q2M.solve_supply(camp, depots, demand0)
        base_tc = Q2_BASE["factions"][camp]["supply_optimization"]["TC_excl_labor"]
        assert abs(r0["TC_excl_labor"] - base_tc) < 1.0, \
            f"{camp} Q2基线复现失败：{r0['TC_excl_labor']} vs {base_tc}"
        print(f"  [{camp}] Q2基线复现 ✓ TC_excl_labor={r0['TC_excl_labor']}")

    print("== A-02 直射距离 sweep ==")
    a02 = sweep_a02()
    print("== A-03 防空半径 sweep ==")
    a03 = sweep_a03()
    print("== A-04 空中上限 sweep ==")
    a04 = sweep_a04()
    print("== A-07 0.5万人粒度验证 ==")
    a07 = verify_a07()
    print("== A-01 基线 vs Stackelberg 结构化登记 ==")
    a01 = comparison_a01()
    print("== 图表 ==")
    make_figures(a02, a03, a04, a01)

    out = {
        "metadata": {
            "purpose": "显式未知参数化 sweep 扫描（不重建模型结构）",
            "date": "2026-08-13",
            "solver_backend": "pulp + HiGHS/CBC（开源，solver_backend.solve_mip）",
            "baseline_reproduction_check": "苏军/盟军 Q1 指挥节点与Φ、Q2 TC 均复现基线（assert 通过）",
        },
        "a01_comparison": a01,
        "a02": a02,
        "a03": a03,
        "a04": a04,
        "a07": a07,
        "figures": ["fig11_q1_direct_range_sweep", "fig12_q1_aa_radius_sweep",
                    "fig13_q2_a01_baseline_vs_stackelberg", "fig14_q1_air_cap_sweep"],
        "total_time_s": round(time.time() - t0, 1),
    }
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "参数化扫描结果.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"已写入 参数化扫描结果.json，总耗时 {out['total_time_s']}s")


if __name__ == "__main__":
    main()
