#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
response3d.py — 3D 响应面配方（双参数联合灵敏度，论文限 1 张）

选型依据：图表类型参考库 决策表「双参数联合响应」行 + 「3D 响应面画法规范」节。
用法（与其他 recipe 一致）：
  1. 改 PARAMETERS 区块（数据 / 标签 / 色板）
  2. 直接运行本文件：输出 PDF+PNG 双格式 + visual_qa 程序自检
  3. CORE 区块为画法规范固化（底部投影等高线 / pane.fill=False / 视角），一般不动；
     题目特定自定义（最优点标注等）只改 CORE 末尾的【自定义区】。
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# 依赖路径：.trae/code_templates（visualization_style）+ figure-studio/scripts（visual_qa）
_ROOT = Path(__file__).resolve().parents[2]          # .trae/skills
sys.path.insert(0, str(_ROOT / ".." / "code_templates"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from visualization_style import (  # noqa: E402
    setup_style, save_figure, CU_TEXTWIDTH_IN, COLORMAPS, CMASHER_ACTIVE,
)


# ============================================================
# PARAMETERS 区块（改这里）
# ============================================================
# --- 数据：X/Y 为参数网格，Z 为目标函数值（三矩阵同形状）---
PARAM_X = np.linspace(0.4, 2.0, 60)      # 参数一取值范围
PARAM_Y = np.linspace(2.0, 12.0, 60)     # 参数二取值范围
X, Y = np.meshgrid(PARAM_X, PARAM_Y)
# 示例目标函数（占位）：替换为真实目标函数 Z = f(X, Y)
Z = (np.sin(1.2 * X * Y / 8.0) * X - 0.03 * (Y - 7.0) ** 2
     + 0.15 * X * Y - 0.4 * X ** 2)

# --- 标签（图内不放中文大标题；坐标轴标签可含中文，标题职能归 caption）---
XL = "参数 $\\alpha$"
YL = "参数 $\\beta$"
ZL = "目标函数值"
CBAR_LABEL = ZL

# --- 色板（感知均匀系：顺序 sunburst / 发散 fusion，见 COLORMAPS）---
CMAP = COLORMAPS["diverging"] if CMASHER_ACTIVE else "RdBu_r"

# --- 导出 ---
OUT = "response3d"        # 输出文件名（不含扩展名，PDF+PNG 双格式）
DTYPE_SAFE = True         # 保留 True：筛除 NaN/Inf 防止曲面破洞


# ============================================================
# CORE 区块（画法规范固化，一般不动）
# ============================================================
setup_style()

if DTYPE_SAFE:
    Z = np.where(np.isfinite(Z), Z, np.nan)
    zmin, zmax = float(np.nanmin(Z)), float(np.nanmax(Z))

W = CU_TEXTWIDTH_IN
fig = plt.figure(figsize=(W, W * 0.85), dpi=300)
ax = fig.add_subplot(111, projection="3d")

# 曲面：浅灰细网格 + 抗锯齿 + 光照阴影（观感层）
surf = ax.plot_surface(X, Y, Z, cmap=CMAP, linewidth=0.15,
                       rstride=1, cstride=1, antialiased=True,
                       shade=True, alpha=0.95, vmin=zmin, vmax=zmax)

# 底部投影等高线（读数层，标准做法：zdir='z' + offset=zmin）
ax.contourf(X, Y, Z, zdir="z", offset=zmin, cmap=CMAP,
            alpha=0.55, levels=10, vmin=zmin, vmax=zmax)

# 视角：峰谷不被遮挡（多峰结构可在【自定义区】加双视角子图）
ax.view_init(elev=25, azim=-135)

# 期刊观感关键：去掉 3D 默认背景面板 + 浅灰细网格
for p in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
    p.fill = False
    p.set_edgecolor("#cfcfcf")
    p.set_linewidth(0.6)
ax.grid(True, alpha=0.12, linewidth=0.4)

# 色条（紧凑）与坐标轴标签
cbar = fig.colorbar(surf, shrink=0.6, aspect=20, pad=0.08)
cbar.set_label(CBAR_LABEL)
ax.set_xlabel(XL, labelpad=12)
ax.set_ylabel(YL, labelpad=12)
ax.set_zlabel(ZL, labelpad=12)
ax.tick_params(labelsize=7, pad=2)

# ============================================================
# 【自定义区】题目特定标注（仅改这里，禁止图内中文大标题）
# ============================================================
# 示例：标注曲面最高点（最优候选点）
best = np.unravel_index(np.nanargmax(Z), Z.shape)
ax.scatter([X[best]], [Y[best]], [Z[best]],
           color="#D55E00", s=26, depthshade=False)
ax.text(X[best], Y[best], float(Z[best]) * 0.9 if zmin < 0 else float(Z[best]) * 0.985,
        " 最高点", fontsize=8, ha="left", color="#7A3B00")

# ============================================================
# 程序自检 + 导出
# ============================================================
from visual_qa import audit_figure  # noqa: E402

problems = audit_figure(fig)
has_error = any(lv == "ERROR" for lv, _, _ in problems)
save_figure(fig, OUT)
print(f"[response3d] 输出 {OUT}.pdf / {OUT}.png，自检 {'有 ERROR' if has_error else '通过'}")