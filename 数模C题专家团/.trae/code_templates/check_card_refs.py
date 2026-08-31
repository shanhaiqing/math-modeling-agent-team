#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_card_refs.py — 数据方法卡片 → 代码模板 引用完整性机查（C 版）
================================================================
用途：校验每张数据方法卡片头部的「代码模板」元数据行指向的模板文件真实存在，
     消灭"卡片引用不存在文件"的悬空引用。

规则（与卡片头部元数据行格式强一致，改动格式须同步本脚本）：
  1. 卡片含 `> 代码模板：` 元数据行时，行内所有 `code_templates/xxx.py`
     路径必须存在于 .trae/code_templates/ 下，缺失 → FAIL。
  2. 卡片不含该元数据行 → SKIP（本系统卡片格式不强制该元数据，属合法）。
  3. 元数据行以「无（」开头（自实现 / 待补标注）时不要求路径，属合法 → SKIP。

用法：
  python .trae/code_templates/check_card_refs.py
退出码：0 = 通过；1 = 存在悬空引用或格式违规。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(HERE, "..", "papers", "数据方法卡片")
TEMPLATES_DIR = HERE
PATH_RE = re.compile(r"code_templates/([\w.]+)")
META_RE = re.compile(r"^\s*> 代码模板：(.*)$")


def main() -> int:
    if not os.path.isdir(CARDS_DIR):
        print(f"FAIL: 卡片目录不存在 {CARDS_DIR}")
        return 1
    card_files = sorted(f for f in os.listdir(CARDS_DIR) if f.endswith(".md"))
    if not card_files:
        print("FAIL: 未发现任何卡片")
        return 1

    total = len(card_files)
    ok_cnt = fail_cnt = skip_cnt = 0
    problems = []

    for f in card_files:
        path = os.path.join(CARDS_DIR, f)
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()

        meta_lines = [META_RE.match(l) for l in lines]
        meta_lines = [m for m in meta_lines if m]
        if not meta_lines:
            skip_cnt += 1
            continue

        refs = []
        for m in meta_lines:
            content = m.group(1)
            refs += PATH_RE.findall(content)
        if refs:
            missing = [r for r in refs if not os.path.exists(os.path.join(TEMPLATES_DIR, r))]
            if missing:
                fail_cnt += 1
                problems.append(f"{f}: 引用不存在的模板 {missing}")
            else:
                ok_cnt += 1
        else:
            # 无路径：须为「无（自实现/待补）」合法标注
            if any("无（" in m.group(1) for m in meta_lines):
                skip_cnt += 1
            else:
                fail_cnt += 1
                problems.append(f"{f}: 代码模板行无路径且无「无（」标注")

    print(f"卡片总数 {total}：路径存在 {ok_cnt}，自实现/待补 {skip_cnt}，失败 {fail_cnt}")
    for p in problems:
        print(f"  [FAIL] {p}")
    if fail_cnt == 0:
        print("引用完整性机查通过：无悬空引用")
        return 0
    print("存在悬空引用或格式违规，需修复")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
