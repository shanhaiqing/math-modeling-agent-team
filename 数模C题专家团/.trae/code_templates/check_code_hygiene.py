#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_code_hygiene.py — 交付代码注释卫生检查（机查版）

[契约] 交付代码（project/*.py）注释不得含内部流程词（C 版，移植自 B 系统同源契约）；
       MODELING 过门机查命中即 ERROR。
[新增] 交付代码禁止含emoji/变体选择符等特殊Unicode，这些字符
       在LaTeX附录Verbatim环境中因Consolas/SimSun字体无字形导致PDF乱码。
[背景] 历史教训：代码模板注释自带流水线术语，随代码继承到交付物，
       支撑材料打包时被迫逐文件清洗，耗费大量时间。防污染在产出时，不在打包时。
检查范围：目标目录下全部 .py 文件的注释行（# 之后）与 docstring（三引号串）；
         新增emoji检查覆盖整个源文件（包括print等字符串常量）。
黑名单：内部流水线术语与内部契约产物名（见 INTERNAL_TERMS）；
        emoji检查范围见 EMOJI_PATTERN（杂项符号+表情符号+变体选择符）。
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

# emoji/特殊Unicode黑名单（这些字符在Consolas/SimSun字体中无字形，导致PDF乱码）
# 范围：
#   - U+2600-U+26FF 杂项符号：含⚠(U+26A0)，但★(U+2605)已在LaTeX字体配置中处理
#   - U+1F300-U+1FAFF 表情符号区：emoji彩色图标，等宽字体均不支持
#   - U+FE00-U+FE0F 变体选择符：不可见字符，导致⚠️组合中️缺失字形
EMOJI_PATTERN = re.compile(
    "["
    "\u26a0"          # ⚠ 单独的警告符号
    "\U0001f300-\U0001faff"  # 表情符号区
    "\ufe00-\ufe0f"  # 变体选择符
    "]"
)
# 放行列表：暂无——本次问题字符全部禁止
EMOJI_ALLOWLIST = set()

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

    # 检查1：注释/docstring中的内部流程词（原有检查）
    for lineno, text in iter_comment_texts(source):
        for m in TERM_PATTERN.finditer(text):
            hits += 1
            error(f"{path}:{lineno}", f"注释含内部流程词 '{m.group(0)}'：{text.strip()[:80]}")

    # 检查2：全文件扫描emoji/特殊Unicode字符（C 版移植）
    # 覆盖注释、docstring、字符串常量所有位置——VerbatimInput会原样输出整个文件
    for lineno, line in enumerate(source.splitlines(), 1):
        for m in EMOJI_PATTERN.finditer(line):
            ch = m.group(0)
            if ch in EMOJI_ALLOWLIST:
                continue
            # 给出字符名称提示
            cp = ord(ch)
            hint = f"U+{cp:04X}"
            if cp == 0x26a0:
                hint += " (⚠ 警告符号)"
            elif 0xfe00 <= cp <= 0xfe0f:
                hint += " (变体选择符，不可见但会导致字体缺失)"
            hits += 1
            error(f"{path}:{lineno}",
                  f"含emoji/特殊Unicode字符 {hint}，LaTeX附录Verbatim环境中字体不支持会乱码；"
                  f"请替换为纯文本：{line.strip()[:80]}")

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
