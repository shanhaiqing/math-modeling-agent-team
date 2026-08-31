#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
package_support_materials.py — 支撑材料一键打包（机查版）

[契约] COMPLIANCE 阶段由编排器运行（C 版，移植自 B 系统同源契约）；
       只收代码+数据+图表，内部契约 JSON 一律不入包；终扫未过不得交付。
流程：暂存（复制 project/ 下 *.py + data/ + figures/）→ 压缩 → 体积校验（≤20MB）
      → 解压终扫（内部流程词黑名单 + 绝对路径 + 身份信息模式）→ 清理临时目录。
用法:
  python package_support_materials.py [--project project] [--out 支撑材料.zip]
         [--max-mb 20] [--exclude 文件名 ...]
退出码: 0 = 打包成功且终扫通过；1 = 终扫命中或体积超限；2 = 用法错误
输出:   控制台逐条打印 + 写 packaging_report.json
"""
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# 终扫黑名单：内部流程词（与 check_code_hygiene.py 同源）
INTERNAL_TERMS = [
    "HG0", "HG1", "HG2", "HG3", "裁决", "反思门", "红队", "机查", "契约",
    "惯例", "编排", "Agent", "agent", "subagent", "Subagent", "LLM",
    "solution.json", "modeling_plan", "feature_fingerprint", "result_bundle",
    "decision_logs", "stage5", "pipeline_state", "AGENTS.md", "handoff",
    "防过拟合", "审批清单", "复盘",
]
# 绝对路径模式（可移植性）与身份信息模式（匿名性）
PATH_PATTERN = re.compile(r"[A-Za-z]:\\\\?Users|/home/|/Users/|C:\\\\Users")
IDENTITY_PATTERN = re.compile(r"大学|学院|学校|赛区|参赛队|队员|导师|学号")
TERM_PATTERN = re.compile("|".join(re.escape(t) for t in INTERNAL_TERMS))

FINDINGS = []


def error(loc, msg):
    FINDINGS.append({"level": "ERROR", "location": loc, "message": msg})


def ok(msg):
    FINDINGS.append({"level": "PASS", "location": "", "message": msg})


def stage(project_dir, stage_dir, excludes):
    """复制交付内容到暂存目录：*.py（排除名单）+ data/ + figures/。"""
    count = 0
    (stage_dir / "data").mkdir(parents=True, exist_ok=True)
    (stage_dir / "figures").mkdir(parents=True, exist_ok=True)
    for f in sorted(project_dir.glob("*.py")):
        if f.name in excludes:
            continue
        shutil.copy2(f, stage_dir / f.name)
        count += 1
    for sub in ("data", "figures"):
        src = project_dir / sub
        if src.is_dir():
            for f in sorted(src.iterdir()):
                if f.is_file():
                    shutil.copy2(f, stage_dir / sub / f.name)
                    count += 1
    return count


def final_scan(target_dir):
    """解压终扫：文本文件查黑名单/绝对路径/身份信息；二进制文件跳过。"""
    hits = 0
    for f in sorted(target_dir.rglob("*")):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue  # 二进制（xlsx/pdf/png）跳过
        rel = str(f.relative_to(target_dir))
        for i, line in enumerate(text.splitlines(), 1):
            m = TERM_PATTERN.search(line)
            if m:
                hits += 1
                error(f"{rel}:{i}", f"内部流程词残留 '{m.group(0)}'")
            m = PATH_PATTERN.search(line)
            if m:
                hits += 1
                error(f"{rel}:{i}", f"绝对路径残留 '{m.group(0)}'")
            m = IDENTITY_PATTERN.search(line)
            if m:
                hits += 1
                error(f"{rel}:{i}", f"疑似身份信息 '{m.group(0)}'")
    return hits


def main():
    argv = sys.argv[1:]

    def opt(flag, default):
        if flag in argv:
            return argv[argv.index(flag) + 1]
        return default

    project_dir = Path(opt("--project", "project"))
    out_zip = Path(opt("--out", "支撑材料.zip"))
    max_mb = float(opt("--max-mb", "20"))
    excludes = set()
    if "--exclude" in argv:
        i = argv.index("--exclude")
        excludes = set(argv[i + 1:])

    if not project_dir.is_dir():
        print(f"用法错误：项目目录不存在 {project_dir}")
        sys.exit(2)

    tmp = Path(tempfile.mkdtemp(prefix="pkg_stage_"))
    verify = Path(tempfile.mkdtemp(prefix="pkg_verify_"))
    try:
        stage_dir = tmp / project_dir.name
        stage_dir.mkdir()
        n = stage(project_dir, stage_dir, excludes)
        ok(f"暂存 {n} 个文件（*.py + data/ + figures/）")

        if out_zip.exists():
            out_zip.unlink()
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for f in sorted(stage_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(tmp))
        size_mb = out_zip.stat().st_size / (1024 * 1024)
        if size_mb > max_mb:
            error(str(out_zip), f"压缩包 {size_mb:.2f}MB 超过 {max_mb}MB 上限")
        else:
            ok(f"压缩完成：{out_zip.name} {size_mb:.2f}MB（上限 {max_mb}MB）")

        with zipfile.ZipFile(out_zip) as zf:
            zf.extractall(verify)
        hits = final_scan(verify / project_dir.name)
        if hits == 0:
            ok("解压终扫通过：零内部流程词 / 零绝对路径 / 零身份信息")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(verify, ignore_errors=True)

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    for f in FINDINGS:
        print(f"{f['level']:5s} {f['location']} {f['message']}")
    print(f"汇总：{n_err} ERROR")

    Path("packaging_report.json").write_text(json.dumps(
        {"checker": "package_support_materials", "zip": str(out_zip),
         "size_mb": round(size_mb, 2), "error": n_err, "findings": FINDINGS},
        ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
