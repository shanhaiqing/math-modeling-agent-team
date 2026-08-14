#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_prompt_budget.py — agent prompt 字数机查（全文口径，含 frontmatter）

[契约] AGENTS.md 防过拟合铁律 7：
       建议值 9500（超 → WARN，人工裁定，不阻塞；确为实质内容可保留）；
       平台硬上限 10000（超 → ERROR 必须压缩，否则无法存入 Trae 自定义智能体）。
[执行] rules/orchestrator.md 第 4 节（任意共享文件落地后必跑）。
用法：python check_prompt_budget.py [--budget 9500] [--hard-limit 10000] [--agents-dir <目录>]
"""
import sys
from pathlib import Path


def _arg(flag, default):
    return int(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default


def main():
    budget = _arg("--budget", 9500)      # 建议值：超 → WARN
    hard = _arg("--hard-limit", 10000)   # 平台硬上限：超 → ERROR
    agents_dir = Path(sys.argv[sys.argv.index("--agents-dir") + 1]) if "--agents-dir" in sys.argv \
        else Path(__file__).resolve().parent.parent / "agents"
    errors = warns = 0
    for f in sorted(agents_dir.glob("*.md")):
        n = len(f.read_text(encoding="utf-8"))
        if n > hard:
            errors += 1
            print(f"ERROR {f.name}: {n} 字符——超平台硬上限 {hard}，必须压缩")
        elif n > budget:
            warns += 1
            print(f"WARN  {f.name}: {n} 字符——超建议值 {budget}（未超硬上限 {hard}，人工裁定是否压缩）")
        else:
            print(f"OK    {f.name}: {n} 字符（建议值 {budget}）")
    if errors:
        print(f"ERROR: {errors} 个 prompt 超平台硬上限——必须压缩至 {hard} 以内")
        sys.exit(1)
    if warns:
        print(f"WARN: {warns} 个 prompt 超建议值 {budget}——按铁律 8 优先置换压缩；确为实质内容可保留")
    else:
        print("OK: 全部 prompt 在建议值内")
    sys.exit(0)


if __name__ == "__main__":
    main()
