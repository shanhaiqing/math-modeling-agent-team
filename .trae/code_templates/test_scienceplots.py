# -*- coding: utf-8 -*-
"""验证 setup_style 的 SciencePlots 集成是否生效"""
import matplotlib
matplotlib.use("Agg")
import sys
sys.path.insert(0, ".trae/code_templates")
import visualization_style as vs

vs.setup_style()
print("SCIENCE_STYLE_ACTIVE =", vs.SCIENCE_STYLE_ACTIVE)
print("font.sans-serif  =", vs.plt.rcParams["font.sans-serif"])
print("savefig.dpi      =", vs.plt.rcParams["savefig.dpi"])
print("grid.alpha       =", vs.plt.rcParams.get("grid.alpha"))
print("axes.unicode_minus =", vs.plt.rcParams.get("axes.unicode_minus"))

# 实际出一张带中文的图，验证中文不显示方框
import numpy as np
fig, ax = vs.plt.subplots(figsize=vs.SINGLE_COLUMN)
x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), label="利润变化")
ax.set_xlabel("迭代次数")
ax.set_ylabel("目标值 / 元")
ax.set_title("收敛曲线（中文验证）")
ax.grid(True)
fig.canvas.draw()
print("绘图成功，中文渲染 OK")
vs.plt.close(fig)