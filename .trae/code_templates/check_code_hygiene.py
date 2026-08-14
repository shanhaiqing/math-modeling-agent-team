#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_code_hygiene.py — 交付代码注释卫生检查（机查版）

[契约] 总审批清单 2026-08-B1 P4-a：交付代码（project/*.py）注释不得含内部流程词；
       MODELING 过门机查命中即 ERROR。
[背景] 历史教训：代码模板注释自带流水线术语，随代码继承到交付物，
       支撑材料打包时被迫逐文件清洗，耗费大量时间。防污染在产出时，不在打包时。
检查范围：目标目录下全部 .py 文件的注释行（# 之后）与 docstring（三引号串）。
黑名单：内部流水线术语与内部契约产物名（见 INTERNAL_TERMS）。
用法:
  python check_code_hygiene.py <代码目录> [--report code_hygiene_report.json]
退出码: 0 = 无 ERROR；1 = 存在 ERROR；2 = 用法错误
输出:   控制台逐条打印 + 写 code_hygiene_report.json
"""
import ast
import json
import re
import sys
from pathlib import Path

# 内部流程词黑名单：流水线术语 + 内部契约产物名
INTERNAL_TERMS = [
    "HG0", "HG1", "HG2", "HG3", "裁决", "反思门", "红队", "机查", "契约",
    "惯例", "编排", "Agent", "agent", "subagent", "Subagent", "LLM",
    "solution.json", "modeling_plan", "feature_fingerprint", "result_bundle",
    "decision_logs", "stage5", "pipeline_state", "AGENTS.md", "handoff",
    "防过拟合", "审批清单", "复盘",
]
TERM_PATTERN = re.compile("|".join(re.escape(t) for t in INTERNAL_TERMS))

FINDINGS = []


def error(loc, msg):
    FINDINGS.append({"level": "ERROR", "location": loc, "message": msg})


def ok(msg):
    FINDINGS.append({"level": "PASS", "location": "", "message": msg})


def iter_comment_texts(source):
    """产出 (行号, 文本)：注释行 + docstring/字符串常量中的文本。"""
    for i, line in enumerate(source.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            yield i, stripped
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for off, seg in enumerate(node.value.splitlines()):
                yield node.lineno + off, seg


def check_file(path):
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="utf-8", errors="replace")
    hits = 0
    for lineno, text in iter_comment_texts(source):
        for m in TERM_PATTERN.finditer(text):
            hits += 1
            error(f"{path}:{lineno}", f"注释含内部流程词 '{m.group(0)}'：{text.strip()[:80]}")
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--report")]
    if not args:
        print("用法：python check_code_hygiene.py <代码目录> [--report 路径]")
        sys.exit(2)
    root = Path(args[0])
    if not root.is_dir():
        print(f"用法错误：目录不存在 {root}")
        sys.exit(2)
    report_path = Path("code_hygiene_report.json")
    if "--report" in sys.argv:
        report_path = Path(sys.argv[sys.argv.index("--report") + 1])

    files = sorted(root.rglob("*.py"))
    total = 0
    for f in files:
        total += check_file(f)
    if total == 0:
        ok(f"扫描 {len(files)} 个 .py 文件，注释零内部流程词")

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    for f in FINDINGS[:50]:
        print(f"{f['level']:5s} {f['location']} {f['message']}")
    if len(FINDINGS) > 50:
        print(f"...（共 {len(FINDINGS)} 条，余略，详见报告）")
    print(f"汇总：{n_err} ERROR / {len(files)} 文件扫描")

    report_path.write_text(json.dumps(
        {"checker": "check_code_hygiene", "scanned": len(files),
         "error": n_err, "findings": FINDINGS},
        ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
