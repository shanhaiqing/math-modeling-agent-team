#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_prompt_budget.py — agent prompt 字数预算机查（全文口径 ≤9500）

[契约] AGENTS.md 防过拟合铁律 7（prompt 字数预算 9500，平台上限 10000）；
       口径为**全文字符数**（含 frontmatter，对齐平台整文件限制）。
[执行] rules/orchestrator.md 第 4 节（任意共享文件落地后必跑）。
用法：python check_prompt_budget.py [--budget 9500] [--agents-dir <目录>]
"""
import sys
from pathlib import Path

def main():
    budget = int(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 9500
    agents_dir = Path(sys.argv[sys.argv.index("--agents-dir") + 1]) if "--agents-dir" in sys.argv \
        else Path(__file__).resolve().parent.parent / "agents"
    errors = 0
    for f in sorted(agents_dir.glob("*.md")):
        n = len(f.read_text(encoding="utf-8"))
        status = "OK " if n <= budget else "ERROR"
        if n > budget:
            errors += 1
        print(f"{status} {f.name}: {n} 字符（预算 {budget}）")
    if errors:
        print(f"ERROR: {errors} 个 prompt 超预算——按铁律 8 置换模式压缩（去纯重复指针，不丢实质规则）")
        sys.exit(1)
    print("OK: 全部 prompt 在预算内")
    sys.exit(0)

if __name__ == "__main__":
    main()
