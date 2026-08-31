#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配方：联合分布图（主散点 + 边缘直方图 + colorbar 编码第三维）

适用 claim："X 与 Y 存在〈某种〉关系，且该关系随第三维 Z 演化"
结构：中央散点（颜色=第三维 Z）+ 上/右边缘直方图 + colorbar + 注释框（统计量）
效果参照：华为杯标杆"公转轨道与视线投影"（图 6.16 类构图）。

用法：修改 PARAMETERS 区块的数据来源与标签，CORE 区块一般不动。
依赖：团队 visualization_style.py（样式/配色/保存），visual_qa.py（程序自检）。
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "..", "..", "..", "code_templates"))  # visualization_style
sys.path.insert(0, os.path.join(_here, "..", "scripts"))                     # visual_qa
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

import visualization_style as vs
from visual_qa import audit_figure

# ==================== PARAMETERS（按题目修改） ====================
TITLE_CLAIM = "This figure shows that ___"   # 设计卡一句话职责（不写不出图）
OUT = "figures/fig_joint"                    # 输出主名（自动 .pdf/.png）
XLAB, YLAB, ZLAB = "X 轴（单位）", "Y 轴（单位）", "Z（第三维，单位）"
STATS_TEXT = ""                              # 注释框统计量，如 "r=0.83, n=436"


def load_data():
    """返回 x, y, z 三个等长数组。替换为从 project/results/*.json 读取。"""
    rng = np.random.default_rng(2026)
    t = rng.uniform(0, 2 * np.pi, 400)
    x = np.sin(t) + 0.1 * rng.normal(size=t.size)
    y = np.cos(t) + 0.1 * rng.normal(size=t.size)
    z = t
    return x, y, z


# ==================== CORE（一般不动） ====================

def main():
    assert TITLE_CLAIM != "This figure shows that ___", "先填设计卡一句话职责"
    x, y, z = load_data()
    vs.setup_style()

    W = vs.CU_TEXTWIDTH_IN                    # 0.9\textwidth ≈ 14.6cm，与论文引入宽度 1:1
    fig = plt.figure(figsize=(W, W * 0.78))  # 保持原 2×2 联合图宽高比（≈5.6/7.2）
    gs = GridSpec(2, 2, width_ratios=[4, 1.1], height_ratios=[1.1, 4],
                  hspace=0.05, wspace=0.05, figure=fig)
    ax_main = fig.add_subplot(gs[1, 0])
    ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)

    # 中央散点：颜色编码第三维（顺序色板，色盲安全）
    sc = ax_main.scatter(x, y, c=z, cmap=vs.COLORMAPS["sequential"],
                         s=14, alpha=0.85, linewidths=0)
    ax_main.set_xlabel(XLAB)
    ax_main.set_ylabel(YLAB)
    vs._apply_grid(ax_main)
    cb = fig.colorbar(sc, ax=[ax_main, ax_right], fraction=0.05, pad=0.02)
    cb.set_label(ZLAB, fontsize=9)

    # 边缘直方图（半透明填充，与主图同色系）
    ax_top.hist(x, bins=30, color=vs.COLORS["primary"], alpha=0.55, linewidth=0)
    ax_right.hist(y, bins=30, orientation="horizontal",
                  color=vs.COLORS["primary"], alpha=0.55, linewidth=0)
    for a in (ax_top, ax_right):
        a.tick_params(labelleft=False, labelbottom=False)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)

    if STATS_TEXT:
        vs.annotate_badge(ax_main, STATS_TEXT,
                          xy=(0.03, 0.97), fontsize=8)

    problems = audit_figure(fig)  # 程序自检：缺字/裁切/刻度重叠
    assert not any(lv == "ERROR" for lv, _, _ in problems), "程序自检 ERROR，先修再导出"
    vs.save_figure(fig, OUT)
    plt.close(fig)


if __name__ == "__main__":
    main()
