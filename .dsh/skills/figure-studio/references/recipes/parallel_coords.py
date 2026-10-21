#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配方：平行坐标图（parallel coordinates）——多目标解集 trade-off 全景

适用 claim："多目标优化得到的 Pareto 解集在〈M 个目标〉上呈现〈互补/冲突〉的 trade-off"
结构：每目标一条垂直轴（统一归一化到 0-1），每个解一条折线穿越各轴；
      颜色可编码某个主目标值（顺序色板，无需额外图例）。
典型用途：多目标优化（条件触发：目标数 ≥4）的 Pareto 前沿可视化。

用法：修改 PARAMETERS 区块（DIM_LABELS、DATA 来源），CORE 区块一般不动。
依赖：团队 visualization_style.py（样式/配色/保存），visual_qa.py（程序自检）。
规范：图内不放中文大标题（标题职能由论文 caption 承担）；各轴必须归一化（量纲差异）。
图内语言：缺省 cumcm 可用中文占位。shuwei_en 时 DIM_LABELS 必须全英文。
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
OUT = "figures/fig_parallel_coords"          # 输出主名（自动 .pdf/.png）
DIM_LABELS = ["目标1", "目标2", "目标3", "目标4"]  # 各目标轴名（列数 = DATA 列数）
COLOR_BY = 0                                 # 用第几列目标着色（None = 统一主色）
DATA = np.array([                            # (N, M) 解集，每行一个解、每列一个目标
    [1.0, 0.5, 0.9, 0.2],
    [0.8, 0.6, 0.7, 0.3],
    [0.6, 0.8, 0.4, 0.5],
    [0.4, 0.9, 0.2, 0.7],
])

# ==================== CORE（一般不动） ====================

def load_data():
    """返回 (N, M) 解集数组。替换为从 project/results/*.json 读取。"""
    return np.asarray(DATA, dtype=float)


def main():
    assert TITLE_CLAIM != "This figure shows that ___", "先填设计卡一句话职责"
    data = load_data()
    n, m = data.shape
    assert m == len(DIM_LABELS), "DIM_LABELS 长度须等于 DATA 列数"
    vs.setup_style()

    # min-max 归一化（各目标量纲不同，归一化后才有可比折线）
    dmin = data.min(axis=0)
    dmax = data.max(axis=0)
    rng = dmax - dmin
    rng[rng == 0] = 1.0
    norm = (data - dmin) / rng

    W = vs.CU_TEXTWIDTH_IN
    fig, ax = plt.subplots(figsize=(W, W * 0.7))
    xs = np.arange(m)

    # 颜色：按指定目标着色（顺序色板体现该目标大小）
    if COLOR_BY is not None and n > 1:
        cvals = data[:, COLOR_BY]
        grange = cvals.max() - cvals.min() or 1.0
        normc = (cvals - cvals.min()) / grange
        cmap = plt.get_cmap(vs.COLORMAPS["sequential"])
        colors = [cmap(v) for v in normc]
    else:
        colors = [vs.COLORS["primary"]] * n

    for i in range(n):
        ax.plot(xs, norm[i], color=colors[i], alpha=0.6, linewidth=1.2)

    # 垂直轴 + 轴名
    for j in range(m):
        ax.axvline(j, color="gray", linewidth=0.8, alpha=0.6)
        ax.text(j, -0.08, DIM_LABELS[j], ha="center", va="top", fontsize=8)

    ax.set_xlim(-0.5, m - 0.5)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([0, 0.5, 1])
    ax.set_yticklabels(["min", "0.5", "max"], fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", alpha=0.15, linewidth=0.5)

    problems = audit_figure(fig)
    assert not any(lv == "ERROR" for lv, _, _ in problems), "程序自检 ERROR，先修再导出"
    vs.save_figure(fig, OUT)
    plt.close(fig)


if __name__ == "__main__":
    main()