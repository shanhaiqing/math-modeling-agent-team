#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_abstract_guard.py — 摘要守护机查（LaTeX 版，改编自 cumcm-rebuild-award-abstract 的 abstract_guard.py）

三个子命令：
  locate <paper.tex>    定位摘要正文边界（titlepage 内 minipage 起 → 关键词行前），JSON 报告。
  verify  <a.tex> <b.tex>
                        校验两份论文除摘要正文外逐字符一致（修复回路摘要定稿用，惯例 三.10）。
  audit   <paper.tex>   摘要质量机查（WARN 级不阻塞）：
                        (1) 篇幅分布：纯文本字符数脱离国一基准 [772,1294] → WARN；
                        (2) 段落量化：各问题段（首段总述豁免）无任何数字 → WARN（疑似有方法无结果）；
                        (3) 关键词行加粗：无 \\textbf → WARN（惯例 二.33）。
退出码：0 = 无 ERROR 级问题；1 = 有 ERROR（locate/verify 失败）。
执行时机登记：orchestrator.md 第 4 节。
"""
import argparse
import json
import re
import sys
from pathlib import Path

TITLEPAGE_BEGIN_RE = re.compile(r"\\begin\{titlepage\}")
TITLEPAGE_END_RE = re.compile(r"\\end\{titlepage\}")
MINIPAGE_BEGIN_RE = re.compile(r"\\begin\{minipage\}")
KEYWORDS_RE = re.compile(r"关键词\s*(?:[：:]|$)")
ANCHOR_RE = re.compile(r"\\label\{abstract:end\}")
ABSTRACT_SECTION_RE = re.compile(
    r"\\section\s*\*\s*\{[^}]*摘\s*要[^}]*\}|\\(?:subsection|section)\*?\s*\{[^}]*摘\s*要[^}]*\}"
)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read().lstrip("\ufeff")


def locate_region(text: str):
    """返回 (body_start_idx, body_end_idx, suffix_idx, keywords_idx)。找不到抛 ValueError。"""
    lines = text.splitlines(keepends=True)

    # 摘要区域：优先 titlepage 页；无 titlepage 时退回 \section{摘 要} 节
    tb_idx = next((i for i, l in enumerate(lines) if TITLEPAGE_BEGIN_RE.search(l)), None)
    if tb_idx is not None:
        te_idx = next((i for i in range(tb_idx, len(lines)) if TITLEPAGE_END_RE.search(lines[i])), None)
        if te_idx is None:
            raise ValueError("titlepage 环境未闭合，无法定位摘要页。")
        region_start, region_end = tb_idx, te_idx
    else:
        sec_idx = next((i for i, l in enumerate(lines) if ABSTRACT_SECTION_RE.search(l)), None)
        if sec_idx is None:
            raise ValueError("未找到 \\begin{titlepage} 或 \\section{摘要}，无法唯一定位摘要。")
        region_start, region_end = sec_idx, len(lines) - 1

    region_lines = lines[region_start:region_end + 1]

    kw_rel = next((i for i, l in enumerate(region_lines) if KEYWORDS_RE.search(l)), None)
    if kw_rel is None:
        raise ValueError("摘要区域内未找到关键词行，无法定位摘要正文结尾。")

    # 正文起点：关键词行之前最近的 \begin{minipage} 行之后
    mp_rel = next(
        (i for i in range(kw_rel - 1, -1, -1) if MINIPAGE_BEGIN_RE.search(region_lines[i])),
        None,
    )
    if mp_rel is None:
        raise ValueError("关键词行之前未找到 \\begin{minipage}，摘要正文边界不唯一。")

    body_start = region_start + mp_rel + 1
    body_end = region_start + kw_rel
    suffix_start = body_end  # 关键词行及之后全部视为"摘要外"
    return body_start, body_end, suffix_start


def strip_tex(text: str) -> str:
    """近似纯文本化用于篇幅/数字统计：删注释、保留数学与宏参数内容。"""
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = text.replace("{", " ").replace("}", " ").replace("\\", " ")
    return text


def command_locate(args) -> int:
    try:
        b0, b1, _ = locate_region(read_text(Path(args.paper)))
        lines = read_text(Path(args.paper)).splitlines()
        body = "\n".join(lines[b0:b1]).strip()
        print(json.dumps({
            "body_start_line": b0 + 1,
            "body_end_line": b1,
            "body_chars": len(body),
            "preview": re.sub(r"\s+", " ", body)[:180],
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


def command_verify(args) -> int:
    try:
        orig = read_text(Path(args.original))
        rev = read_text(Path(args.revised))
        o0, o1, os_ = locate_region(orig)
        r0, r1, rs_ = locate_region(rev)
        failures = []
        if orig[:o0] != rev[:r0]:
            failures.append("摘要正文之前的内容发生变化")
        if orig[os_:] != rev[rs_:]:
            failures.append("关键词行及之后的内容发生变化")
        if orig[o0:o1] == rev[r0:r1]:
            failures.append("摘要正文未发生变化")
        if failures:
            print(json.dumps({"passed": False, "failures": failures}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({
            "passed": True,
            "original_body_chars": len(orig[o0:o1].strip()),
            "revised_body_chars": len(rev[r0:r1].strip()),
            "outside_abstract_identical": True,
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


def command_audit(args) -> int:
    problems = []
    try:
        text = read_text(Path(args.paper))
        lines = text.splitlines()
        b0, b1, _ = locate_region(text)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    body_lines = lines[b0:b1]
    body = "".join(body_lines)
    plain = strip_tex(body)

    # (1) 篇幅分布（国一基准 P10-P90 软边界，超出 WARN 不阻塞）
    n_chars = len(re.sub(r"\s", "", plain))
    if n_chars < 772:
        problems.append(("WARN", "摘要篇幅", f"纯文本 {n_chars} 字符 < 国一基准 P10(772)——疑似信息不足，审计门核查六型"))
    elif n_chars > 1294:
        problems.append(("WARN", "摘要篇幅", f"纯文本 {n_chars} 字符 > 国一基准 P90(1294)——疑似冗长或有超页风险，人工裁定"))

    # (2) 段落量化：按空行分段，首段（总述）豁免，其余无数字 → WARN
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    num_pat = re.compile(r"\d+(?:\.\d+)?|\\?%")
    for i, p in enumerate(paras[1:], start=2):
        if not num_pat.search(strip_tex(p)):
            problems.append(("WARN", "段落无量化", f"第 {i} 段无任何数字——疑似有方法无结果（审计六型之 1/2），人工核查"))

    # (3) 关键词行加粗（惯例 二.33）
    kw_line = next((lines[b1 + j] for j in range(0, 8) if b1 + j < len(lines)
                    and KEYWORDS_RE.search(lines[b1 + j])), None)
    if kw_line is not None and "textbf" not in kw_line:
        problems.append(("WARN", "关键词未加粗", "关键词行未使用 \\textbf（惯例 二.33）；摘要正文其余部分禁止加粗"))

    for level, tag, msg in problems:
        print(f"{level}  [{tag}]  {msg}")
    print(f"汇总：{sum(1 for l, _, _ in problems if l == 'WARN')} WARN")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p1 = sub.add_parser("locate", help="定位摘要正文边界")
    p1.add_argument("paper")
    p1.set_defaults(func=command_locate)
    p2 = sub.add_parser("verify", help="校验两份论文仅摘要正文不同")
    p2.add_argument("original")
    p2.add_argument("revised")
    p2.set_defaults(func=command_verify)
    p3 = sub.add_parser("audit", help="摘要质量机查（WARN 级）")
    p3.add_argument("paper")
    p3.set_defaults(func=command_audit)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())