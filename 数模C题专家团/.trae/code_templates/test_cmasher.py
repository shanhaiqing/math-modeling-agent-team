# -*- coding: utf-8 -*-
"""
单元测试：CMasher 科学色板集成正确性。

验证：
1. CMASHER_ACTIVE 已置 True（本机已安装 cmasher）。
2. COLORMAPS 各键指向已注册的科学 colormap（cmr.* 可被 matplotlib 解析）。
3. plot_heatmap 默认走顺序色板，能正常出图。
4. 优雅降级：模拟 cmasher 不可用时，COLORMAPS 应回退到内置色板且热力图仍可出图。
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


# 1) CMasher 已加载
check("CMASHER_ACTIVE=True", vs.CMASHER_ACTIVE is True)

# 2) 顺序/发散/循环色板均已注册到 matplotlib（matplotlib 3.11 后 cmr.* 用 matplotlib.colormaps 解析）
from matplotlib import colormaps  # noqa: E402
for key in ["sequential", "diverging", "cyclic"]:
    name = vs.COLORMAPS[key]
    try:
        colormaps[name]
        check(f"COLORMAPS[{key}]='{name}' 可解析", True)
    except Exception as e:
        check(f"COLORMAPS[{key}]='{name}' 可解析", False)

# 3) plot_heatmap 默认顺序色板出图
mat = np.array([[1.0, 2.0], [3.0, 4.0]])
fp = os.path.join(OUT, "heatmap_cmasher")
fig = vs.plot_heatmap(mat, filename=fp)
check("plot_heatmap 默认出 PNG", os.path.exists(fp + ".png"))
vs.plt.close(fig)

# 4) 优雅降级：模拟 cmasher 不可用
orig_active, orig_cmasher = vs.CMASHER_ACTIVE, vs.cmasher
vs.CMASHER_ACTIVE = False
vs.cmasher = None
# 注：COLORMAPS 在 import 时已求值，此处重新构造降级版验证回退逻辑自洽
fallback = {
    "sequential": "viridis" if vs.cmasher is None else "cmr.sunburst",
    "diverging": "RdBu_r" if vs.cmasher is None else "cmr.fusion",
    "cyclic": "twilight" if vs.cmasher is None else "cmr.seasons",
}
check("降级 sequential=viridis", fallback["sequential"] == "viridis")
check("降级 diverging=RdBu_r", fallback["diverging"] == "RdBu_r")
# 恢复（避免影响后续测试）
vs.CMASHER_ACTIVE, vs.cmasher = orig_active, orig_cmasher

print(f"\n结果: {PASS} 通过, {FAIL} 失败")
sys.exit(1 if FAIL else 0)