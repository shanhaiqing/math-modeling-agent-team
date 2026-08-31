#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_tex_numbers.py — 论文正文数值 vs solution.json 跨产物一致性机查（WARN 级）

[背景] paper-writer 消费 solution.json 写论文的环节原先无机查，数值漂移
       （solution.json 记 123.45、论文写 123.50）只能靠 reviewer 人工复核发现。
[方法] 抽取 paper.tex 正文"高精度数值"（≥2 位小数的浮点数 / ≥4 位整数），
       与 solution.json 全部数值叶子做容差匹配（相对误差 ≤0.5% 视为命中，
       容忍四舍五入）；未命中 → WARN 供 reviewer 裁定
       （参数值、年份、排版尺寸等合法未命中由人工剔除，不自动判错）。
[级别] WARN-only：未命中不阻塞流水线（exit 恒 0）；仅输入缺失/解析失败 exit 2。
[执行] rules/orchestrator.md §4（WRITING → 下一阶段，与 latex_compliance 同批）。
用法：python check_tex_numbers.py <paper.tex> <solution.json> [--report]
报告：tex_number_check_report.json（paper.tex 同目录，--report 时落盘）
"""
import json
import re
import sys
from pathlib import Path

# 高精度数值：≥2 位小数浮点（123.45）或 ≥4 位整数（12345）
NUM_PAT = re.compile(r"(?<![\d.\\])\d+\.\d{2,}(?![\d.])|(?<![\d.\\])\d{4,}(?![\d.])")
YEAR_PAT = re.compile(r"^(19|20)\d{2}$")
# 排版/引用类命令所在行整体跳过（图尺寸、标签、引用编号等非论文数值）
SKIP_LINE = re.compile(r"\\(includegraphics|label|ref|eqref|cite|begin|end|setlength|pagestyle|ctexset|bibliography)")
TOL = 0.005  # 相对容差（四舍五入容忍）


def collect_leaves(obj, out):
    """递归收集 solution.json 的全部数值叶子。"""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_leaves(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_leaves(v, out)


def strip_tex(text):
    """去注释、去 thebibliography 环境（文献年份等不参与比对）。"""
    text = re.sub(r"(?<!\\)%.*", "", text)
    return re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", text, flags=re.S)


def extract_tex_numbers(text):
    """抽取正文高精度数值，返回 {数值: 首次出现行号}。"""
    found = {}
    for ln, line in enumerate(text.splitlines(), 1):
        if SKIP_LINE.search(line):
            continue
        for m in NUM_PAT.finditer(line):
            tok = m.group(0)
            if YEAR_PAT.match(tok):
                continue
            v = float(tok)
            if v not in found:
                found[v] = ln
    return found


def is_hit(v, leaves):
    """容差命中判定：相对误差 ≤TOL（零值精确相等兜底）。"""
    return any(v == s or (s != 0 and abs(v - s) / abs(s) <= TOL) for s in leaves)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)
    tex_path, sol_path = Path(args[0]), Path(args[1])
    if not tex_path.is_file() or not sol_path.is_file():
        print("FATAL: 输入文件不存在")
        sys.exit(2)

    leaves = []
    try:
        collect_leaves(json.loads(sol_path.read_text(encoding="utf-8")), leaves)
    except Exception as e:
        print(f"FATAL: solution.json 解析失败：{e}")
        sys.exit(2)
    tex_numbers = extract_tex_numbers(strip_tex(tex_path.read_text(encoding="utf-8")))

    unmatched = [{"value": v, "line": ln} for v, ln in sorted(tex_numbers.items())
                 if not is_hit(v, leaves)]

    result = {"tex": str(tex_path), "solution": str(sol_path),
              "leaf_count": len(leaves), "tex_number_count": len(tex_numbers),
              "warn_count": len(unmatched), "unmatched": unmatched}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if "--report" in sys.argv:
        out = tex_path.parent / "tex_number_check_report.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if unmatched:
        print(f"WARN: {len(unmatched)} 个正文数值未命中 solution.json（容差 {TOL:.1%}）"
              f"——供 reviewer 逐条裁定，合法未命中（参数值/排版数）不阻塞")
    else:
        print("OK: 全部高精度正文数值均命中 solution.json")
    sys.exit(0)  # WARN-only，不阻塞


if __name__ == "__main__":
    main()
