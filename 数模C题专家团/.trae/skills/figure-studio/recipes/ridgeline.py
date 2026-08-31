#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配方：山脊图（ridgeline / joyplot）——多组分布形态纵向层叠对比

适用 claim："〈3-6 组〉对象的〈指标〉分布形态存在〈位移/展宽/偏态〉差异"
效果参照：华数杯标杆"三组电路硬模块尺寸分布"（图 2 类构图）。
优势：比分面直方图省版面、比重叠 KDE 不遮挡，组间位移一目了然。

用法：修改 PARAMETERS 区块；组数建议 3-6（>6 改多面板）。
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "..", "..", "..", "code_templates"))  # visualization_style
sys.path.insert(0, os.path.join(_here, "..", "scripts"))                     # visual_qa
import matplotlib.pyplot as plt
import numpy as np

import visualization_style as vs
from visual_qa import audit_figure

# ==================== PARAMETERS（按题目修改） ====================
TITLE_CLAIM = "This figure shows that ___"
OUT = "figures/fig_ridgeline"
XLAB = "指标（单位）"
GROUP_LABELS = None      # 组名列表；None 用 "组1..组N"
OVERLAP = 0.6            # 层叠程度 0.4-0.8，越大越紧凑


def load_data():
    """返回 [组1数组, 组2数组, ...]。替换为从 project/results/*.json 读取。"""
    rng = np.random.default_rng(2026)
    return [rng.normal(loc=1.0 * i, scale=0.4 + 0.1 * i, size=500) for i in range(4)]


# ==================== CORE（一般不动） ====================

def main():
    assert TITLE_CLAIM != "This figure shows that ___", "先填设计卡一句话职责"
    groups = load_data()
    labels = GROUP_LABELS or [f"组{i + 1}" for i in range(len(groups))]
    vs.setup_style()

    xs = np.linspace(min(g.min() for g in groups), max(g.max() for g in groups), 400)
    fig, ax = plt.subplots(figsize=(vs.CU_TEXTWIDTH_IN, 0.9 * len(groups) + 1.6))

    from scipy.stats import gaussian_kde
    for i, (g, lb) in enumerate(zip(groups, labels)):
        kde = gaussian_kde(g)
        ys = kde(xs)
        ys = ys / ys.max()                      # 归一化后层叠
        base = i * OVERLAP
        color = vs.COLORS["palette"][i % len(vs.COLORS["palette"])]
        ax.fill_between(xs, base, base + ys, color=color, alpha=0.55, linewidth=0)
        ax.plot(xs, base + ys, color=color, linewidth=1.2)
        ax.axhline(base, color="gray", linewidth=0.5, alpha=0.5)
        ax.text(xs.min(), base + 0.08, lb, fontsize=9, va="bottom")

    ax.set_yticks([])
    ax.set_xlabel(XLAB)
    ax.set_ylim(-0.05, (len(groups) - 1) * OVERLAP + 1.1)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    problems = audit_figure(fig)
    assert not any(lv == "ERROR" for lv, _, _ in problems), "程序自检 ERROR，先修再导出"
    vs.save_figure(fig, OUT)
    plt.close(fig)


if __name__ == "__main__":
    main()
