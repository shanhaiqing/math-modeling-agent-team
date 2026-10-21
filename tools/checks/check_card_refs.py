#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_card_refs.py — 优化方法卡片 → 代码模板 引用完整性机查
================================================================
用途：校验每张优化方法卡片头部的「代码模板」元数据行指向的模板文件真实存在，
     消灭"卡片引用不存在文件"的悬空引用（2026-08 曾发现 9 处悬空的根治手段）。

规则（与卡片头部元数据行格式强一致，改动格式须同步本脚本）：
  1. 每张卡片必须含至少一行 `> 代码模板：` 元数据，缺失 → FAIL。
  2. 该行内所有 `code_templates/xxx.py` 路径必须存在于 tools/checks/ 下，缺失 → FAIL。
  3. 该行以「无（」开头（自实现 / 待补标注）时不要求路径，属合法 → SKIP。

用法：
  python tools/checks/check_card_refs.py
  python tools/checks/check_card_refs.py --cards-dir <目录> [--allow-missing-meta]
缺省只扫优化方法卡片，且缺少「代码模板」行仍为 FAIL。
数据方法卡片没有该行，扫描时加 --allow-missing-meta。
退出码：0 = 通过；1 = 存在悬空引用或格式违规。
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = HERE
PATH_RE = re.compile(r"code_templates/([\w.]+)")
META_RE = re.compile(r"^\s*> 代码模板：(.*)$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards-dir", default=os.path.join(HERE, "..", "papers", "优化方法卡片"))
    ap.add_argument("--allow-missing-meta", action="store_true")
    args = ap.parse_args()
    CARDS_DIR = args.cards_dir
    allow_missing = args.allow_missing_meta
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
            if allow_missing:
                skip_cnt += 1
                continue
            fail_cnt += 1
            problems.append(f"{f}: 缺少头部「代码模板」元数据行")
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
