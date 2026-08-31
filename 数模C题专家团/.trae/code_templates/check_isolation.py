#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_isolation.py — 信息隔离泄漏审计（复盘前编排器强制执行）

[契约] AGENTS.md 信息隔离节：参照论文提取物强制入 decision_logs/_quarantine/，
       禁止散放；@calibration-analyzer 为唯一授权读者，其他 agent 产出不得含参照论文内容。
[执行] rules/orchestrator.md 第 4 节（CALIBRATION → RETRO 转换前必跑）。

检查项：
  1. decision_logs/ 根下（及项目根）散放的提取物文件（ref_*/ocr_*/_ocr_* 命名特征）→ ERROR
  2. 非授权 agent 产出（retro_modeling/retro_writing/retro_review/paper.tex/handoff_notes*）
     内容含 --signature 特征串 → ERROR
  3. 含特征串的 calibration 产出缺节级隔离声明（惯例 C-1 分层标注）→ WARN

用法：python check_isolation.py --project-root <项目根> [--signature 特征串 ...] [--report]
"""
import argparse, json, re, sys
from pathlib import Path

EXTRACT_PAT = re.compile(r"^(ref_|ocr_|_ocr_).+\.(txt|json|png|jpg|md)$", re.IGNORECASE)
UNAUTHORIZED = ["retro_modeling.md", "retro_writing.md", "retro_review.md",
                "paper.tex", "handoff_notes_1.md", "handoff_notes_2.md",
                "s1_reflection.md", "s2_reflection.md", "s3_reflection.md", "s4_reflection.md"]
ISOLATION_MARK = re.compile(r"隔离节|分层标注|仅 @?calibration-analyzer 与主智能体可读")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--signature", nargs="*", default=[])
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"FATAL: 项目根不存在 {root}"); sys.exit(2)

    errors, warns = [], []

    # 检查 1：提取物散放（_quarantine/ 之外）
    for d in [root, root / "decision_logs"]:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and EXTRACT_PAT.match(f.name):
                errors.append({"item": f.name,
                               "msg": f"参照论文提取物散放于 {d.name}/，须移入 decision_logs/_quarantine/"})

    # 检查 2/3：内容泄漏扫描
    if args.signature:
        dl = root / "decision_logs"
        for name in UNAUTHORIZED:
            f = dl / name
            if not f.is_file():
                f = root / name
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for sig in args.signature:
                if sig in text:
                    errors.append({"item": f.name, "msg": f"非授权产出含参照论文特征串「{sig}」"})
        for name in ["calibration_report.md", "calibration_log.md", "retro_calibration.md",
                     "retrospective.md"]:
            f = dl / name
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            if any(sig in text for sig in args.signature) and not ISOLATION_MARK.search(text):
                warns.append({"item": f.name, "msg": "含参照论文特征串但未检出节级隔离声明（惯例 C-1）"})

    result = {"project_root": str(root), "error_count": len(errors),
              "warn_count": len(warns), "errors": errors, "warns": warns}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        (root / "isolation_check_report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
