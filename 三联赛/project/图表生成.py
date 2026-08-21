#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表生成.py — 全部图表（PDF+PNG 双格式，300dpi，统一走 visualization_style）
图1 战场节点与Q1部署分布图（双方）
图2 Q1部署构成堆叠柱状图
图3 Q2补给路径网络图（苏军示例+盟军）
图4 Q2成本分层构成柱状图
图5 Q2灵敏度Tornado图
图6 Q2护航策略转换临界点图
图7 Q3苏军主攻方向与夺控序列图
图8 Q3盟军转移生存概率对比（MC分布）
图9 算法总体流程图
图10 Q3生存概率-风险缩放敏感性折线图
"""
import json
import os
import sys

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from visualization_style import (setup_style, save_figure, COLORS, COLORMAPS,
                                 plot_tornado, SINGLE_COLUMN, DOUBLE_COLUMN, SQUARE)
from common_data import (load_graph, connected_components, cross_faction_edges,
                         TARGET_NODES, UNIT_TYPES)

POS, CAMP, DEF, EDGE_LEN, ADJ, DEGREE = load_graph()
NODES = list(POS.keys())
MAIN = set(max(connected_components(NODES, ADJ), key=len))
HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
RESULTS = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

with open(os.path.join(RESULTS, "q1_result.json"), encoding="utf-8") as f:
    Q1 = json.load(f)
with open(os.path.join(RESULTS, "q2_result.json"), encoding="utf-8") as f:
    Q2 = json.load(f)
with open(os.path.join(RESULTS, "q3_result.json"), encoding="utf-8") as f:
    Q3 = json.load(f)
with open(os.path.join(RESULTS, "validation_result.json"), encoding="utf-8") as f:
    VAL = json.load(f)

setup_style()


def base_map(ax):
    """底图：节点按阵营着色，防御强度为半径。"""
    for n in NODES:
        x, y = POS[n]
        c = "#d62728" if CAMP[n] == "苏军" else "#1f77b4"
        ax.scatter(x, y, s=12 + 40 * DEF[n], c=c, alpha=0.45, edgecolors="none")
    for (a, b), L in EDGE_LEN.items():
        ax.plot([POS[a][0], POS[b][0]], [POS[a][1], POS[b][1]],
                color="gray", linewidth=0.3, alpha=0.35)
    ax.set_aspect("equal")
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")


# ---------- 图1 部署分布 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, camp in zip(axes, ["苏军", "盟军"]):
    base_map(ax)
    info = Q1["factions"][camp]
    # 部署节点（按数量）
    dep = {}
    for key, v in info["deploy"].items():
        n = int(key.split("@")[1])
        dep[n] = dep.get(n, 0) + v
    for n, v in dep.items():
        ax.scatter(*POS[n], s=60 + v * 0.05, facecolors="none",
                   edgecolors="black", linewidths=1.6, marker="o")
    # 指挥节点
    z = info["command_node"]
    ax.scatter(*POS[z], s=260, marker="*", facecolors="gold",
               edgecolors="black", linewidths=1.2, zorder=5)
    ax.annotate(f"指挥{z}", POS[z], fontsize=8, xytext=(6, 6),
                textcoords="offset points")
    for b in info["command_backups"]:
        ax.scatter(*POS[b], s=110, marker="*", facecolors="lightyellow",
                   edgecolors="gray", zorder=4)
    # 防空
    for p in info["aa_nodes"]:
        ax.scatter(*POS[p], s=90, marker="^", facecolors="none",
                   edgecolors="green", linewidths=1.4, zorder=4)
    ax.set_title(f"{camp}最优部署（★指挥节点 △防空 圈=部署量）")
handles = [mpatches.Patch(color="#d62728", alpha=0.5, label="苏军节点"),
           mpatches.Patch(color="#1f77b4", alpha=0.5, label="盟军节点"),
           plt.Line2D([], [], marker="*", color="gold", linestyle="none",
                      markersize=12, label="指挥节点"),
           plt.Line2D([], [], marker="^", color="green", linestyle="none",
                      markersize=8, label="防空据点")]
axes[1].legend(handles=handles, loc="upper right", fontsize=8)
save_figure(fig, os.path.join(FIG, "fig1_deployment_map"))
plt.close(fig)

# ---------- 图2 部署构成堆叠柱 ----------
fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
camps = ["苏军", "盟军"]
bottom = np.zeros(2)
unit_colors = {"动员兵": "#7f7f7f", "轻型": "#2ca02c", "中型": "#ff7f0e",
               "重型": "#d62728", "火炮": "#9467bd", "空中": "#8c564b"}
for u in UNIT_TYPES:
    vals = []
    for camp in camps:
        s = sum(v for key, v in Q1["factions"][camp]["deploy"].items()
                if key.startswith(u + "@"))
        vals.append(s)
    ax.bar(camps, vals, bottom=bottom, label=u, color=unit_colors[u],
           edgecolor="black", linewidth=0.6)
    bottom += np.array(vals, dtype=float)
ax.set_ylabel("部署数量（动员兵=万人，其余=辆/门/架）")
ax.set_title("问题1：双方部署构成（空中为≤10%上限内部署）")
ax.legend(fontsize=8)
save_figure(fig, os.path.join(FIG, "fig2_deployment_composition"))
plt.close(fig)

# ---------- 图3 补给路径网络 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, camp in zip(axes, camps):
    base_map(ax)
    info = Q2["factions"][camp]
    for dp in info["depots"]:
        ax.scatter(*POS[dp], s=200, marker="s", facecolors="gold",
                   edgecolors="black", zorder=5)
        ax.annotate(f"仓{dp}", POS[dp], fontsize=7, xytext=(4, 4),
                    textcoords="offset points")
    for r in info["supply_optimization"]["routes"]:
        p = r["path"]
        xs = [POS[n][0] for n in p]; ys = [POS[n][1] for n in p]
        lw = 0.8 + r["flow_t_day"] * 0.06
        style = "-" if r["escort"] else "--"
        color = "#2ca02c" if r["escort"] else "#ff7f0e"
        ax.plot(xs, ys, linestyle=style, linewidth=lw, color=color, alpha=0.85)
    ax.set_title(f"{camp}补给网络（实线=护航 虚线=无护航 宽=流量）")
handles = [plt.Line2D([], [], color="#2ca02c", linewidth=2, label="护航路径"),
           plt.Line2D([], [], color="#ff7f0e", linewidth=2, linestyle="--",
                      label="无护航路径"),
           plt.Line2D([], [], marker="s", color="gold", linestyle="none",
                      markersize=10, label="仓库")]
axes[1].legend(handles=handles, loc="upper right", fontsize=8)
save_figure(fig, os.path.join(FIG, "fig3_supply_routes"))
plt.close(fig)

# ---------- 图4 成本分层 ----------
fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
cats = ["运输", "护航", "破交损失", "人力"]
keys = ["C_trans", "C_escort", "C_loss", "C_labor"]
x = np.arange(len(cats)); wbar = 0.38
for i, camp in enumerate(camps):
    so = Q2["factions"][camp]["supply_optimization"]
    vals = [so[k] for k in keys]
    ax.bar(x + (i - 0.5) * wbar, vals, wbar, label=camp,
           color=COLORS["palette"][i], edgecolor="black", linewidth=0.6)
    for j, v in enumerate(vals):
        ax.text(x[j] + (i - 0.5) * wbar, v, f"{v:.0f}", ha="center",
                va="bottom", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("成本（元/日）")
ax.set_title("问题2：后勤成本分层构成")
ax.legend()
save_figure(fig, os.path.join(FIG, "fig4_cost_decomposition"))
plt.close(fig)

# ---------- 图5 Tornado ----------
scan = VAL["sensitivity_q2"]["scans"]
params, sens = [], []
for pname, rows in scan.items():
    # 取最接近 ±20% 的扰动点（各参数扫描均含 0.8/1.2 点）
    lo_r = min(rows, key=lambda r: abs(r["scale"] - 0.8))
    hi_r = min(rows, key=lambda r: abs(r["scale"] - 1.2))
    params.append(pname + "(苏军)")
    sens.append((hi_r["TC_苏军"] - lo_r["TC_苏军"]) / VAL["sensitivity_q2"]["base_TC"]["苏军"] * 100)
    params.append(pname + "(盟军)")
    sens.append((hi_r["TC_盟军"] - lo_r["TC_盟军"]) / VAL["sensitivity_q2"]["base_TC"]["盟军"] * 100)
plot_tornado(params, sens, xlabel="目标值变化（±20%参数扰动，%）",
             title="问题2：后勤总成本灵敏度（Tornado）",
             filename=os.path.join(FIG, "fig5_tornado_q2"))

# ---------- 图6 护航临界点 ----------
fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
rows = VAL["q2_escort_critical"]["scan"]
xs = [r["risk_scale"] for r in rows]
ax.plot(xs, [r["TC_free"] for r in rows], "o-", color=COLORS["primary"],
        label="优化护航（模型最优）")
ax.plot(xs, [r["TC_no_escort"] for r in rows], "s--", color=COLORS["quaternary"],
        label="强制无护航")
crit = VAL["q2_escort_critical"]["critical_risk_scale"]
if crit:
    ax.axvline(crit, color="gray", linestyle=":", linewidth=1.2)
    ax.annotate(f"护航策略临界点\nrisk缩放≈{crit}", (crit, ax.get_ylim()[0]),
                fontsize=8, xytext=(8, 20), textcoords="offset points")
ax.set_xlabel("破交风险缩放系数")
ax.set_ylabel("双方合计后勤成本（元/日，不含人力）")
ax.set_title("问题2：护航策略转换临界点")
ax.legend()
save_figure(fig, os.path.join(FIG, "fig6_escort_critical"))
plt.close(fig)

# ---------- 图7 进攻方案 ----------
fig, ax = plt.subplots(figsize=SQUARE)
base_map(ax)
atk = Q3["soviet_attack"]
a0, a1 = atk["main_axis"]["edge"]
ax.annotate("", xy=POS[a1], xytext=POS[a0],
            arrowprops=dict(arrowstyle="-|>", color="red", lw=3))
ax.scatter(*POS[a0], s=150, marker="s", color="red", zorder=5)
seq = atk["capture_sequence"]
for i in range(len(seq) - 1):
    ax.annotate("", xy=POS[seq[i + 1]], xytext=POS[seq[i]],
                arrowprops=dict(arrowstyle="-|>", color="darkred", lw=1.8,
                                linestyle="--"))
for i, n in enumerate(seq):
    ax.scatter(*POS[n], s=120, marker="o", facecolors="none",
               edgecolors="darkred", linewidths=2, zorder=5)
    ax.annotate(str(i + 1), POS[n], fontsize=9, fontweight="bold",
                color="darkred", xytext=(5, 5), textcoords="offset points")
ax.set_title(f"问题3：苏军主攻方向（{a0}→{a1}）与夺控序列")
save_figure(fig, os.path.join(FIG, "fig7_attack_plan"))
plt.close(fig)

# ---------- 图8 生存概率对比（人员口径） ----------
fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
mc_ok = Q3["ally_withdrawal"]["comm_ok"]["monte_carlo"]
mc_lost = Q3["ally_withdrawal"]["comm_lost"]["monte_carlo"]
names = ["通信畅通\n集中调度", "通信中断\n分散预案"]
means = [mc_ok["mean_survival"], mc_lost["mean_survival"]]
errs = [[m - lo for m, lo in zip(means, [mc_ok["ci95_low"], mc_lost["ci95_low"]])],
        [hi - m for m, hi in zip(means, [mc_ok["ci95_high"], mc_lost["ci95_high"]])]]
bars = ax.bar(names, means, width=0.5, color=[COLORS["tertiary"], COLORS["quaternary"]],
              edgecolor="black", linewidth=0.8, yerr=errs, capsize=8)
for b, m in zip(bars, means):
    ax.text(b.get_x() + b.get_width() / 2, m + 0.02, f"{m:.3f}",
            ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("人员生存概率（MC均值，95%CI误差棒）")
ax.set_ylim(0, 1)
diff = Q3["ally_withdrawal"]["survival_difference"]
ax.set_title(f"问题3：通信畅通与中断两情景人员生存概率对比（畅通-中断差={diff:.3f}，各2000次MC）\n"
             "（人员加权口径，误差棒=95% CI；装备随建制伴随，不进入生存概率加权）")
save_figure(fig, os.path.join(FIG, "fig8_survival_comparison"))
plt.close(fig)

# ---------- 图9 算法流程图 ----------
fig, ax = plt.subplots(figsize=(9, 6.5))
ax.axis("off")
boxes = [
    (0.5, 0.94, "数据层：附件一/二加载 → 图结构/连通分量/几何核验（坐标=km）", "#dbe9f6"),
    (0.5, 0.82, "问题1 MIP：覆盖系数预计算 → 指挥节点Top6候选枚举 → HiGHS分支定界\n→ 部署x[u][n] + 防空Stage-B最大覆盖", "#d6e8d0"),
    (0.5, 0.66, "问题2 MIP：需求=部署×消耗率 → 仓库选址 → 每OD 3候选路径枚举\n→ flow/z 0-1规划（McCormick线性化护航-损失耦合）→ 成本四分层", "#fdeedc"),
    (0.5, 0.50, "对抗层：Stackelberg最坏情形（敌破交预算Top-K投放）对比基线", "#f8d7da"),
    (0.5, 0.36, "问题3：主攻方向评分 → 贪心夺控序列 → Lanchester蒙特卡洛评估\n盟军转移（人员口径）：人员容量分配+装备伴随+最短路+殿后 vs 分散预案 → MC人员生存概率×2000", "#e8d5f0"),
    (0.5, 0.20, "验证层：灵敏度±5/10/20% · 策略临界点扫描 · 多算例3场景\n· MC模型验证（解析vs仿真偏差<5%）· 简化项含/不含对比", "#fff3cd"),
    (0.5, 0.07, "输出：求解结果（status/MIPGap/solve_time 求解器原生元数据）+ 图表", "#e2e3e5"),
]
for x, y, text, color in boxes:
    ax.add_patch(mpatches.FancyBboxPatch((x - 0.42, y - 0.045), 0.84, 0.09,
                                         boxstyle="round,pad=0.01",
                                         facecolor=color, edgecolor="black",
                                         linewidth=1.0))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.2)
for i in range(len(boxes) - 1):
    ax.annotate("", xy=(0.5, boxes[i + 1][1] + 0.05), xytext=(0.5, boxes[i][1] - 0.05),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.3))
ax.set_title("算法总体流程图", fontsize=12)
save_figure(fig, os.path.join(FIG, "fig9_algorithm_flowchart"))
plt.close(fig)

# ---------- 图10 Q3 风险敏感性 ----------
fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
rows = VAL["sensitivity_q3"]
xs = [r["risk_scale"] for r in rows]
ax.plot(xs, [r["surv_comm_ok"] for r in rows], "o-", color=COLORS["tertiary"],
        label="通信畅通")
ax.plot(xs, [r["surv_comm_lost"] for r in rows], "s--", color=COLORS["quaternary"],
        label="通信中断")
ax.set_xlabel("拦截风险缩放系数（±20%）")
ax.set_ylabel("人员生存概率")
ax.set_title("问题3：人员生存概率对拦截风险的敏感性")
ax.legend()
save_figure(fig, os.path.join(FIG, "fig10_q3_risk_sensitivity"))
plt.close(fig)

print("全部 10 张图已生成（PDF+PNG）")
