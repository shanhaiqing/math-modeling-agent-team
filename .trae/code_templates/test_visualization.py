# -*- coding: utf-8 -*-
"""
单元测试：纯可视化封装函数（plot_confint / plot_errorbar）的正确性验证。

验证三件事：
1. 正常输入能正确出图（PDF+PNG 存在、坐标轴范围与输入一致）。
2. 输入校验能拦截明显传错（长度不一致 / 区间不自洽），不静默画错。
3. 不承担任何统计计算——传入的各点数值应原样反映到坐标轴范围。
"""
import matplotlib
matplotlib.use("Agg")
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import visualization_style as vs

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_out")
os.makedirs(OUT, exist_ok=True)

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}")


# --- 用例 1：plot_confint 正常出图，坐标轴范围与输入一致 ---
x = np.array([1.0, 2.0, 3.0, 4.0])
y_mean = np.array([10.0, 20.0, 30.0, 40.0])
y_lower = np.array([9.0, 18.0, 27.0, 36.0])
y_upper = np.array([11.0, 22.0, 33.0, 44.0])
fp = os.path.join(OUT, "confint")
fig = vs.plot_confint(x, y_mean, y_lower, y_upper, filename=fp)
check("plot_confint 生成 PNG", os.path.exists(fp + ".png"))
check("plot_confint 生成 PDF", os.path.exists(fp + ".pdf"))
ax = fig.axes[0] if fig.axes else None
# 坐标轴 x 范围应覆盖 [1,4]，y 范围应覆盖 [9,44]
xl, xr = ax.get_xlim()
yl, yr = ax.get_ylim()
check("x 范围覆盖输入", xl <= 1.0 and xr >= 4.0)
check("y 范围覆盖区间", yl <= min(y_lower) and yr >= max(y_upper))
vs.plt.close(fig)

# --- 用例 2：plot_confint 输入校验——长度不一致应报错 ---
try:
    vs.plot_confint(x, y_mean, y_lower[:-1], y_upper, filename=fp + "_bad")
    check("长度不一致被拦截", False)
except ValueError:
    check("长度不一致被拦截", True)

# --- 用例 3：plot_confint 输入校验——区间不自洽应报错 ---
try:
    vs.plot_confint(x, y_mean, y_mean + 5, y_upper, filename=fp + "_bad2")
    check("区间不自洽被拦截", False)
except ValueError:
    check("区间不自洽被拦截", True)

# --- 用例 4：plot_errorbar 正常出图 ---
fp2 = os.path.join(OUT, "errorbar")
fig2 = vs.plot_errorbar(x, y_mean, yerr=2.0, filename=fp2)
check("plot_errorbar 生成 PNG", os.path.exists(fp2 + ".png"))
check("plot_errorbar 生成 PDF", os.path.exists(fp2 + ".pdf"))
vs.plt.close(fig2)

print(f"\n结果: {PASS} 通过, {FAIL} 失败")
sys.exit(1 if FAIL else 0)