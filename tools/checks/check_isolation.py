#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_isolation.py — 校准/复盘提取物泄漏审计（复盘前编排器强制执行；比赛活流水线不调用）

[契约] 进化工具包/隔离规程.md：参照论文提取物强制入 decision_logs/_quarantine/，
       禁止散放。赛时 agent 可检索同题论文（AGENTS.md 开放检索）；本脚本只拦校准提取物散放与写入非授权产出。
[执行] 进化工具包（CALIBRATION → RETRO 转换前必跑）。

检查项：
  1. 全项目递归扫描（_quarantine/.venv/.git 等除外）散放的提取物文件
     （ref_*/ocr_*/_ocr_* 命名特征）→ ERROR
  2. 非授权 agent 产出（retro_modeling/retro_writing/retro_review/paper.tex/
     handoff_notes_1-3/fix_round*/s1-s4_reflection/solution.json 等）
     内容含 --signature 特征串 → ERROR
  3. 含特征串的 calibration 产出（含 handoff_notes_4）缺节级隔离声明
     （惯例 C-1 分层标注）→ WARN

用法：python check_isolation.py --project-root <项目根> [--signature 特征串 ...] [--report]
签名规程：--signature 由编排器按 rules/orchestrator.md §8 第 4 步从 _quarantine/
提取物中现场提取（≥3 条高区分度特征串）；无签名的空跑仅检查散放、不查内容泄漏。
"""
import argparse, json, re, sys
from pathlib import Path

EXTRACT_PAT = re.compile(r"^(ref_|ocr_|_ocr_).+\.(txt|json|png|jpg|md)$", re.IGNORECASE)
EXCLUDE_DIRS = {"_quarantine", ".venv", "venv", ".git", "node_modules", "__pycache__"}
UNAUTHORIZED = {"retro_modeling.md", "retro_writing.md", "retro_review.md",
                "paper.tex", "handoff_notes_1.md", "handoff_notes_2.md", "handoff_notes_3.md",
                "s1_reflection.md", "s2_reflection.md", "s3_reflection.md", "s4_reflection.md",
                "guided_questions_trace.md", "method_card_matching.md",
                "abstract_candidates.md", "modeling_plan.json",
                "solution.json", "feature_fingerprint.json", "术语表.json"}
UNAUTHORIZED_PREFIX = ("fix_round",)   # fix_round*.md（paper-writer 修复轮产物）
CALIBRATION_FILES = {"calibration_report.md", "calibration_log.md", "retro_calibration.md",
                     "retrospective.md", "handoff_notes_4.md", "fix_order.md"}
ISOLATION_MARK = re.compile(r"隔离节|分层标注|仅 @?calibration-analyzer 与主智能体可读")


def iter_project_files(root: Path):
    """递归枚举项目文件，排除隔离区与环境目录。"""
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        yield p

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

    # 检查 1：提取物散放（_quarantine/ 之外任何位置，全项目递归）
    for f in iter_project_files(root):
        if EXTRACT_PAT.match(f.name):
            errors.append({"item": str(f.relative_to(root)),
                           "msg": f"参照论文提取物散放（{f.parent.relative_to(root)}/），须移入 decision_logs/_quarantine/"})

    # 检查 2/3：内容泄漏扫描
    if args.signature:
        for f in iter_project_files(root):
            unauth = f.name in UNAUTHORIZED or any(f.name.startswith(p) for p in UNAUTHORIZED_PREFIX)
            calib = f.name in CALIBRATION_FILES
            if not unauth and not calib:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            hits = [sig for sig in args.signature if sig in text]
            if not hits:
                continue
            rel = str(f.relative_to(root))
            if unauth:
                for sig in hits:
                    errors.append({"item": rel, "msg": f"非授权产出含参照论文特征串「{sig}」"})
            elif not ISOLATION_MARK.search(text):
                warns.append({"item": rel, "msg": "含参照论文特征串但未检出节级隔离声明（惯例 C-1）"})

    result = {"project_root": str(root), "error_count": len(errors),
              "warn_count": len(warns), "errors": errors, "warns": warns}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        (root / "isolation_check_report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
