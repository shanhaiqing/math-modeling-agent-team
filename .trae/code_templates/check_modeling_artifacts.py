#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_modeling_artifacts.py — MODELING 产物格式与代码卫生机查（总审批清单 P11-b）

[契约] 总审批清单 P11：把三项确定性检查从"靠注意力"转为机查，
       缺陷从 COMPLIANCE 打包阶段提前到 MODELING 过门拦截。
检查项：
  [P11-F] figures/ PDF+PNG 双格式配对：按文件名主干配对，
          单格式（只有 PDF 或只有 PNG）→ ERROR；总数 <6 → ERROR
  [P11-A] project/*.py 绝对路径扫描：命中 C:\\ / /Users/ / /home/ 等
          硬编码绝对路径 → ERROR（应改为 __file__ 派生相对路径）
  [P11-G] 商业求解器 import 扫描：命中 gurobi/cplex/mosek/xpress → ERROR
          （硬约束：求解器必须使用开源后端）
用法:
  python check_modeling_artifacts.py <项目根> [--report 路径]
  figures 目录默认 <项目根>/result_bundle/figures/（回退 <项目根>/project/figures/）
  代码目录默认 <项目根>/project/
退出码: 0 = 无 ERROR；1 = 存在 ERROR；2 = 用法错误
输出:   控制台逐条打印 + 写 modeling_artifacts_report.json（项目根）
"""
import json
import re
import sys
from pathlib import Path

FINDINGS = []

# 绝对路径模式（Windows 盘符 / Unix 家目录 / 常见根目录）
ABS_PATH_PAT = re.compile(
    r"[A-Za-z]:[\\/]|(?<![\w.])/Users/|(?<![\w.])/home/|(?<![\w.])/root/|(?<![\w.])C:\\\\",
)
# 商业求解器 import（含 from/import 两种写法）
COMMERCIAL_SOLVER_PAT = re.compile(
    r"^\s*(?:import|from)\s+(gurobipy|cplex|docplex|mosek|xpress)\b",
    re.MULTILINE,
)


def error(rule, loc, msg):
    FINDINGS.append({"level": "ERROR", "rule": rule, "location": loc, "message": msg})


def warn(rule, loc, msg):
    FINDINGS.append({"level": "WARN", "rule": rule, "location": loc, "message": msg})


def ok(rule, msg):
    FINDINGS.append({"level": "PASS", "rule": rule, "location": "", "message": msg})


def check_figure_pairs(fig_dir):
    """P11-F：PDF+PNG 双格式配对 + 总数下限。"""
    if not fig_dir.is_dir():
        error("P11-F", str(fig_dir), "figures 目录不存在")
        return
    pdfs = {p.stem for p in fig_dir.glob("*.pdf")}
    pngs = {p.stem for p in fig_dir.glob("*.png")}
    only_pdf = sorted(pdfs - pngs)
    only_png = sorted(pngs - pdfs)
    for s in only_pdf:
        error("P11-F", f"{s}.pdf", "缺配对 PNG（须 PDF+PNG 双格式）")
    for s in only_png:
        error("P11-F", f"{s}.png", "缺配对 PDF（须 PDF+PNG 双格式）")
    n_pairs = len(pdfs & pngs)
    if n_pairs < 6:
        error("P11-F", str(fig_dir), f"双格式图表仅 {n_pairs} 组 < 6（红线要求 ≥6 张）")
    elif not only_pdf and not only_png:
        ok("P11-F", f"{n_pairs} 组图表全部 PDF+PNG 配对齐全")


def check_abs_paths(code_dir):
    """P11-A：代码绝对路径扫描。"""
    hits = 0
    for py in sorted(code_dir.glob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        for ln, line in enumerate(text.splitlines(), 1):
            # 跳过注释行中的示例说明（# 开头）不豁免——绝对路径无论何处都违规
            if ABS_PATH_PAT.search(line):
                error("P11-A", f"{py.name}:{ln}", f"硬编码绝对路径：{line.strip()[:80]}")
                hits += 1
    if hits == 0:
        ok("P11-A", f"扫描 {len(list(code_dir.glob('*.py')))} 个脚本，零绝对路径")


def check_commercial_solvers(code_dir):
    """P11-G：商业求解器 import 扫描。"""
    hits = 0
    for py in sorted(code_dir.glob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        for m in COMMERCIAL_SOLVER_PAT.finditer(text):
            ln = text[: m.start()].count("\n") + 1
            error("P11-G", f"{py.name}:{ln}", f"商业求解器 import：{m.group(0).strip()}")
            hits += 1
    if hits == 0:
        ok("P11-G", "零商业求解器 import（开源后端约束满足）")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法：python check_modeling_artifacts.py <项目根> [--report 路径]")
        sys.exit(2)
    root = Path(args[0])
    if not root.is_dir():
        print(f"用法错误：目录不存在 {root}")
        sys.exit(2)
    report_path = root / "modeling_artifacts_report.json"
    if "--report" in sys.argv:
        report_path = Path(sys.argv[sys.argv.index("--report") + 1])

    # figures 目录：result_bundle 优先（过门时已复制），回退 project/figures
    fig_dir = root / "result_bundle" / "figures"
    if not fig_dir.is_dir():
        fig_dir = root / "project" / "figures"
    code_dir = root / "project"

    check_figure_pairs(fig_dir)
    if code_dir.is_dir():
        check_abs_paths(code_dir)
        check_commercial_solvers(code_dir)
    else:
        error("P11-A", str(code_dir), "project/ 目录不存在")

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    n_warn = sum(1 for f in FINDINGS if f["level"] == "WARN")
    icon = {"ERROR": "✗", "WARN": "⚠", "PASS": "✓"}
    for f in FINDINGS:
        loc = f" {f['location']}" if f["location"] else ""
        print(f"{icon[f['level']]} {f['level']:<5} [{f['rule']}]{loc} {f['message']}")
    print(f"\n汇总: {n_err} ERROR / {n_warn} WARN")

    report_path.write_text(json.dumps(
        {"checker": "check_modeling_artifacts", "root": str(root),
         "summary": {"ERROR": n_err, "WARN": n_warn},
         "findings": FINDINGS},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已写入: {report_path}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
