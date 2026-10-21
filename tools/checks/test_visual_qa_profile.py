# -*- coding: utf-8 -*-
"""shuwei_en 出图剖面：西文衬线、图内 CJK ERROR；缺省 cumcm 零行为差。"""
import matplotlib
matplotlib.use("Agg")
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "skills" / "figure-studio" / "scripts"))

import visualization_style as vs
from visual_qa import audit_figure, scan

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


def _fig(xlabel):
    fig, ax = vs.plt.subplots(figsize=(4.0, 2.4))
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel(xlabel)
    ax.set_ylabel("y")
    return fig


# 1) 英文赛：Times 系衬线，SimSun 不得排在 serif 首位
vs.setup_style("shuwei_en")
serif = list(vs.plt.rcParams["font.serif"])
family = list(vs.plt.rcParams["font.family"])
check("shuwei_en font.family 含 serif", any("serif" == x or x == "serif" for x in family) or family == ["serif"])
check("shuwei_en serif 首位非 SimSun", serif[0] != "SimSun")
check("shuwei_en serif 首位为西文候选",
      serif[0] in vs._WESTERN_SERIF_CANDIDATES or serif[0] == "DejaVu Serif")
check("shuwei_en 回退栈不含 SimSun", "SimSun" not in serif)

# 2) 英文赛：图内中文 → ERROR；纯英文不因缺 CJK 字体报缺字形
fig_zh = _fig("迭代次数")
probs_zh = audit_figure(fig_zh, contest_profile="shuwei_en")
vs.plt.close(fig_zh)
check("shuwei_en 中文轴标 ERROR",
      any(lv == "ERROR" and "中文" in (rule + msg) for lv, rule, msg in probs_zh))
check("shuwei_en 中文不报缺字形",
      not any(rule == "缺字形" for _, rule, _ in probs_zh))

fig_en = _fig("Iteration")
probs_en = audit_figure(fig_en, contest_profile="shuwei_en")
vs.plt.close(fig_en)
check("shuwei_en 英文轴标无 CJK ERROR",
      not any(lv == "ERROR" and "中文" in (rule + msg) for lv, rule, msg in probs_en))
check("shuwei_en 英文不报缺字形",
      not any(rule == "缺字形" for _, rule, _ in probs_en))

# 3) 国赛：中文轴标不得被当成「图内禁中文」
vs.setup_style("cumcm")
fig_c = _fig("迭代次数")
probs_c = audit_figure(fig_c, contest_profile="cumcm")
vs.plt.close(fig_c)
check("cumcm 中文不触发图内中文 ERROR",
      not any(rule == "图内中文" for _, rule, _ in probs_c))

# 4) 切回国赛后 CJK 字体回到栈内（本机有 SimSun 时）
if vs._cjk_font:
    check("cumcm 恢复后 serif/sans 含 CJK",
          vs._cjk_font in list(vs.plt.rcParams["font.serif"])
          or vs._cjk_font in list(vs.plt.rcParams["font.sans-serif"]))

# 5) scan 缺省不做 PDF CJK（临时英文 PDF 含中文也不该在 cumcm 下 ERROR）
out = HERE / "_test_out"
out.mkdir(exist_ok=True)
fig_s = _fig("成本")
vs.save_figure(fig_s, str(out / "fig_cjk_probe"))
vs.plt.close(fig_s)
sc_cumcm = scan(str(out / "fig_cjk_probe.png"), contest_profile="cumcm")
check("cumcm scan 不对 PNG 报图内中文",
      not any(rule == "图内中文" for ps in sc_cumcm.values() for _, rule, _ in ps))
sc_en = scan(str(out / "fig_cjk_probe.png"), contest_profile="shuwei_en")
# PDF 抽字依赖 pymupdf；抽到则必须 ERROR，抽不到则本项跳过不算失败
en_cjk = [(lv, rule, msg) for ps in sc_en.values() for lv, rule, msg in ps if rule == "图内中文"]
if en_cjk:
    check("shuwei_en scan PDF 抽出 CJK 则 ERROR", all(lv == "ERROR" for lv, _, _ in en_cjk))
else:
    print("[SKIP] shuwei_en scan 未从 PDF 抽出 CJK（audit_figure 已覆盖）")

print(f"\n结果: {PASS} 通过, {FAIL} 失败")
sys.exit(1 if FAIL else 0)
