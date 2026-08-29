#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配方：雨云图（raincloud）——分布 + 散点 + 箱线三合一（小样本全信息）

适用 claim："〈K 组〉样本的〈指标〉分布呈〈位移/展宽/偏态〉差异，且需展示原始点"
结构（水平版，每组一行）：
  上半：核密度"雨云"（cloud，半边密度曲线）
  中间：箱线图（box，中位数与四分位距）
  下半：抖动散点（rain，每一个原始样本点）
典型用途：小样本（每 n < 200）结果分组，一图同时给全"原始点 + 分布形状 + 汇总统计"。

用法：修改 PARAMETERS 区块（load_data 返回分组数组），CORE 区块一般不动。
依赖：团队 visualization_style.py，visual_qa.py，scipy（gaussian_kde）。
规范：图内不放中文大标题（标题职能由论文 caption 承担）；图中标注总样本数 N。
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "..", "..", "..", "code_templates"))  # visualization_style
sys.path.insert(0, os.path.join(_here, "..", "scripts"))                     # visual_qa
import numpy as np
import matplotlib.pyplot as plt

import visualization_style as vs
from visual_qa import audit_figure

# ==================== PARAMETERS（按题目修改） ====================
TITLE_CLAIM = "This figure shows that ___"   # 设计卡一句话职责（不写不出图）
OUT = "figures/fig_raincloud"                # 输出主名（自动 .pdf/.png）
XLAB = "指标（单位）"
GROUP_LABELS = None                          # 组名列表；None 用 "组1..组N"
CLOUD_H = 0.6                                # 雨云相对高度（越大云端越高）


def load_data():
    """返回 [组1数组, 组2数组, ...]。替换为从 project/results/*.json 读取。"""
    rng = np.random.default_rng(2026)
    return [rng.normal(loc=1.0 * i, scale=0.3 + 0.1 * i, size=80) for i in range(3)]


# ==================== CORE（一般不动） ====================

def main():
    assert TITLE_CLAIM != "This figure shows that ___", "先填设计卡一句话职责"
    groups = [np.asarray(g, dtype=float) for g in load_data()]
    labels = GROUP_LABELS or [f"组{i + 1}" for i in range(len(groups))]
    vs.setup_style()

    from scipy.stats import gaussian_kde

    n = len(groups)
    W = vs.CU_TEXTWIDTH_IN
    fig, ax = plt.subplots(figsize=(W, 1.2 * n))

    for i, (g, lb) in enumerate(zip(groups, labels)):
        color = vs.COLORS["palette"][i % len(vs.COLORS["palette"])]

        # 1) rain：抖动散点（基线下方向下，每个原始样本点）
        jitter = np.random.default_rng(2026 + i).normal(0, 0.04, size=len(g))
        ax.scatter(g, i - jitter, s=10, color=color, alpha=0.5, linewidths=0)

        # 2) box：箱线图（水平，置于基线 i）
        bp = ax.boxplot(g, positions=[i], vert=False, widths=0.35,
                        patch_artist=True, manage_ticks=False)
        for patch in bp["boxes"]:
            patch.set_facecolor(color)
            patch.set_alpha(0.35)
        for el in bp["medians"]:
            el.set_color("black")
            el.set_linewidth(1.2)
        for el in bp["whiskers"] + bp["caps"]:
            el.set_color("black")
            el.set_linewidth(1.0)

        # 3) cloud：半边核密度（基线上方向外）
        if len(g) > 2 and float(g.std()) > 0:
            kde = gaussian_kde(g)
            xgrid = np.linspace(float(g.min()), float(g.max()), 200)
            dens = kde(xgrid)
            dens = dens / dens.max() * CLOUD_H
            ax.fill_between(xgrid, i, i + dens, color=color, alpha=0.35, linewidth=0)
            ax.plot(xgrid, i + dens, color=color, linewidth=1.0)

    N = sum(len(g) for g in groups)
    ax.text(0.99, 0.02, f"N={N}", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="gray")
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel(XLAB)
    ax.set_ylim(-0.5, n - 0.5 + CLOUD_H + 0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="x", alpha=0.15, linewidth=0.5)

    problems = audit_figure(fig)
    assert not any(lv == "ERROR" for lv, _, _ in problems), "程序自检 ERROR，先修再导出"
    vs.save_figure(fig, OUT)
    plt.close(fig)


if __name__ == "__main__":
    main()