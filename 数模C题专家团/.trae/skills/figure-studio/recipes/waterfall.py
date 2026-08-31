#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配方：瀑布图（waterfall）——从基线到最终值的逐项增减分解

适用 claim："〈总量〉从基线 X 经 N 项增减（+a, -b, ...）累积到 Y"
结构：柱形按顺序排列，每根柱子底部 = 前序累积值；颜色区分正增量（绿）与负增量（红），
      并叠加起点/终点参考线。
典型用途：成本分层建模的"成本分解归因"、指标从基线到最优值的变化拆解。

用法：修改 PARAMETERS 区块（LABELS/CHANGES 与数据来源），CORE 区块一般不动。
依赖：团队 visualization_style.py（样式/配色/保存），visual_qa.py（程序自检）。
规范：图内不放中文大标题（标题职能由论文 caption 承担）；数值可溯源到 solution.json。
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
OUT = "figures/fig_waterfall"                # 输出主名（自动 .pdf/.png）
START = 0.0                                  # 基线/初始值（如总成本的初始估计）
LABELS = ["采购", "检测", "装配", "拆解", "调换", "报废"]   # 各项名称（顺序即展示顺序）
CHANGES = [100, -20, 80, -15, 30, -10]       # 各项变化量（正=增，负=减，与 LABELS 等长）
XLAB = "成本项"
YLAB = "累积成本（单位）"


def load_data():
    """返回 (labels, changes, start)。替换为从 project/results/*.json / solution.json 读取。"""
    return list(LABELS), list(CHANGES), START


# ==================== CORE（一般不动） ====================

def main():
    assert TITLE_CLAIM != "This figure shows that ___", "先填设计卡一句话职责"
    labels, changes, start = load_data()
    changes = np.asarray(changes, dtype=float)
    assert changes.shape[0] == len(labels), "LABELS 与 CHANGES 长度须一致"
    vs.setup_style()

    W = vs.CU_TEXTWIDTH_IN
    fig, ax = plt.subplots(figsize=(W, W * 0.7))

    # 累积底边（每根柱子的起点）
    bottoms = np.concatenate([[start], start + np.cumsum(changes)])[:-1]
    x = np.arange(len(labels))
    pos_color = vs.COLORS["tertiary"]     # 正增量（绿=增益）
    neg_color = vs.COLORS["quaternary"]   # 负增量（红=减少）

    for i, (dv, bt) in enumerate(zip(changes, bottoms)):
        color = pos_color if dv >= 0 else neg_color
        ax.bar(i, dv, bottom=bt, color=color, alpha=vs.BAR_ALPHA,
               edgecolor="black", linewidth=1.2, width=0.6)
        va = "bottom" if dv >= 0 else "top"
        ax.text(i, bt + dv, f"{dv:+.1f}", ha="center", va=va, fontsize=8)

    # 起点 / 终点参考线
    ax.axhline(start, color="gray", linewidth=0.8, linestyle="--", alpha=0.6)
    final = start + changes.sum()
    ax.axhline(final, color=vs.COLORS["primary"], linewidth=1.0,
               linestyle="--", alpha=0.8)
    ax.text(len(labels) - 0.5, final, f"最终 {final:.1f}", ha="center", va="bottom",
            fontsize=9, color=vs.COLORS["primary"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_xlabel(XLAB)
    ax.set_ylabel(YLAB)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", alpha=0.15, linewidth=0.5)

    problems = audit_figure(fig)
    assert not any(lv == "ERROR" for lv, _, _ in problems), "程序自检 ERROR，先修再导出"
    vs.save_figure(fig, OUT)
    plt.close(fig)


if __name__ == "__main__":
    main()