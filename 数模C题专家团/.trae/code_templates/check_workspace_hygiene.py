#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_workspace_hygiene.py — 工作区卫生检查（机查版）

[契约] 总审批清单 2026-08-B2 P5-a：扫描项目根设计外垃圾，命中即 ERROR；
       执行时机为每次阶段转换前。
[背景] 历史教训：一次性工具脚本、result_bundle 重复副本、LaTeX 编译副产物、
       临时目录散落项目根，两次人工清理才除净，且撑爆目录列表消耗 token。
       产物注册表 + manifest 机查保障"该有什么"，本机查保障"不该有什么"。
检查范围：项目根第一层（文件与目录），不递归深入白名单目录。
检查项：
  1. 未登记临时脚本（test_*/tmp_*/extract_*/ocr_*/pdf_to_*/scratch_* 等模式）
  2. result_bundle/ 内文件在项目根的重复副本
  3. LaTeX 编译副产物（*.aux/*.log/*.out/*.toc/*.synctex.gz/*.minted/_minted/ 等）
  4. 未登记临时目录（temp_images/temp/tmp/_tmp 等模式）
白名单：隐藏目录（.git/.trae/.venv 等）与 --allow 显式豁免项不参与检查。
用法:
  python check_workspace_hygiene.py <项目根> [--allow 名称,名称,...] [--report 路径]
退出码: 0 = 无 ERROR；1 = 存在 ERROR；2 = 用法错误
输出:   控制台逐条打印 + 写 workspace_hygiene_report.json
"""
import fnmatch
import json
import sys
from pathlib import Path

# 未登记临时脚本模式（项目根第一层的 .py/.tex/.txt 等一次性产物）
TEMP_SCRIPT_PATTERNS = [
    "test_*", "tmp_*", "temp_*", "scratch_*", "extract_*", "ocr_*",
    "pdf_to_*", "*_test.py", "debug_*", "try_*", "xel_*",
]

# LaTeX 编译副产物模式
LATEX_ARTIFACT_PATTERNS = [
    "*.aux", "*.log", "*.out", "*.toc", "*.synctex.gz", "*.minted",
    "*.fls", "*.fdb_latexmk", "*.xdv", "*.bbl", "*.blg",
]
LATEX_ARTIFACT_DIRS = ["_minted"]

# 未登记临时目录模式
TEMP_DIR_PATTERNS = ["temp_images", "temp", "tmp", "_tmp", "_temp"]

# 默认豁免目录（有意保留的工作目录，不参与"设计外垃圾"判定）
ALWAYS_ALLOW_DIRS = {"agent质量排查"}

FINDINGS = []


def error(loc, msg):
    FINDINGS.append({"level": "ERROR", "location": loc, "message": msg})


def ok(msg):
    FINDINGS.append({"level": "PASS", "location": "", "message": msg})


def matches_any(name, patterns):
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法：python check_workspace_hygiene.py <项目根> [--allow a,b] [--report 路径]")
        sys.exit(2)
    root = Path(args[0])
    if not root.is_dir():
        print(f"用法错误：目录不存在 {root}")
        sys.exit(2)
    allow = set()
    if "--allow" in sys.argv:
        allow = {s.strip() for s in sys.argv[sys.argv.index("--allow") + 1].split(",") if s.strip()}
    report_path = Path("workspace_hygiene_report.json")
    if "--report" in sys.argv:
        report_path = Path(sys.argv[sys.argv.index("--report") + 1])

    # result_bundle/ 内文件名集合（用于重复副本检查）
    bundle_names = set()
    bundle_dir = root / "result_bundle"
    if bundle_dir.is_dir():
        bundle_names = {p.name for p in bundle_dir.rglob("*") if p.is_file()}

    scanned = 0
    for entry in sorted(root.iterdir()):
        name = entry.name
        if name.startswith(".") or name in allow or name in ALWAYS_ALLOW_DIRS:
            continue
        scanned += 1
        if entry.is_file():
            if matches_any(name, TEMP_SCRIPT_PATTERNS):
                error(name, "未登记临时脚本（一次性工具/试错产物，应删除或移入 decision_logs/）")
            elif matches_any(name, LATEX_ARTIFACT_PATTERNS):
                error(name, "LaTeX 编译副产物滞留工作区（应删除）")
            elif name in bundle_names:
                error(name, f"result_bundle/ 内文件的重复副本（权威副本在 result_bundle/{name}）")
        elif entry.is_dir():
            if name in LATEX_ARTIFACT_DIRS:
                error(name + "/", "LaTeX 编译副产物目录（应删除）")
            elif matches_any(name, TEMP_DIR_PATTERNS):
                error(name + "/", "未登记临时目录（应删除或按隔离规则归位）")

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    if n_err == 0:
        ok(f"扫描项目根 {scanned} 个条目，零设计外垃圾")
    for f in FINDINGS[:50]:
        print(f"{f['level']:5s} {f['location']} {f['message']}")
    print(f"汇总：{n_err} ERROR / {scanned} 条目扫描")

    report_path.write_text(json.dumps(
        {"checker": "check_workspace_hygiene", "scanned": scanned,
         "error": n_err, "findings": FINDINGS},
        ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
