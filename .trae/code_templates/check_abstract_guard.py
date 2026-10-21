#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_abstract_guard.py — 摘要守护机查（LaTeX 版，改编自 cumcm-rebuild-award-abstract 的 abstract_guard.py）

三个子命令：
  locate <paper.tex>    定位摘要正文边界，JSON 报告。
                        cumcm：titlepage 内 minipage 起 → 「关键词」行前。
                        shuwei_en：\\abstract{...} 内、\\label{abstract:end}/\\keywords 之前。
  verify  <a.tex> <b.tex>
                        校验两份论文除摘要正文外逐字符一致（修复回路摘要定稿用，惯例 三.10）。
  audit   <paper.tex>   摘要质量机查（WARN 级不阻塞）：
                        cumcm：(1) 纯文本字符数脱离国一基准 [772,1294] → WARN；
                              (2) 段落量化：各问题段（首段总述豁免）无任何数字 → WARN；
                              (3) 关键词行加粗：无 \\textbf → WARN（惯例 二.33）。
                        shuwei_en：不套国一中文字符窗与关键词 \\textbf；
                              词数过少 WARN；问题段无数字仍 WARN；\\keywords 为空 WARN。

--contest-profile=cumcm|shuwei_zh|shuwei_en 可写在子命令前或后。
缺省时读 paper.tex 同目录或 cwd 的 pipeline_state.json；非法/缺失视为 cumcm。
shuwei_zh 走中文摘要边界（与 cumcm 相同）。

退出码：0 = 无 ERROR 级问题；1 = verify 未通过；2 = locate 失败。
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
ABSTRACT_SECTION_RE = re.compile(
    r"\\section\s*\*\s*\{[^}]*摘\s*要[^}]*\}|\\(?:subsection|section)\*?\s*\{[^}]*摘\s*要[^}]*\}"
)
ABSTRACT_CMD_RE = re.compile(r"\\abstract\s*\{")
KEYWORDS_CMD_RE = re.compile(r"\\keywords\s*\{")
ABSTRACT_END_LABEL_RE = re.compile(r"\\label\{abstract:end\}")

LEGAL_PROFILES = ("cumcm", "shuwei_zh", "shuwei_en")
SHUWEI_EN_WORD_FLOOR = 100


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read().lstrip("\ufeff")


def resolve_contest_profile(cli_value, tex_path):
    """--contest-profile 优先；否则读 pipeline_state.json；非法/缺失 → cumcm。"""
    if cli_value:
        v = cli_value.strip().lower()
        return v if v in LEGAL_PROFILES else "cumcm"
    candidates = []
    if tex_path is not None:
        candidates.append(Path(tex_path).parent / "pipeline_state.json")
    candidates.append(Path.cwd() / "pipeline_state.json")
    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        v = str(data.get("contest_profile") or "").strip().lower()
        return v if v in LEGAL_PROFILES else "cumcm"
    return "cumcm"


def peel_profile(argv):
    """抽出任意位置的 --contest-profile，其余 argv 交给 argparse。"""
    profile = None
    out = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--contest-profile="):
            profile = a.split("=", 1)[1].strip()
        elif a == "--contest-profile":
            if i + 1 >= len(argv):
                raise SystemExit("用法错误：--contest-profile 需要 cumcm|shuwei_zh|shuwei_en")
            profile = argv[i + 1].strip()
            i += 1
        else:
            out.append(a)
        i += 1
    return profile, out


def _line_offset(text, line_idx):
    """splitlines(keepends=True) 下第 line_idx 行的字符起点。"""
    if line_idx <= 0:
        return 0
    lines = text.splitlines(keepends=True)
    if line_idx >= len(lines):
        return len(text)
    return sum(len(ln) for ln in lines[:line_idx])


def _matching_brace(text, open_idx):
    """open_idx 指向 '{'，返回配对 '}' 的下标。跳过注释与 \\ 转义。"""
    if open_idx >= len(text) or text[open_idx] != "{":
        raise ValueError("摘要定位：内部错误，未落在 '{{' 上。")
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        c = text[i]
        if c == "%" and (i == 0 or text[i - 1] != "\\"):
            nl = text.find("\n", i)
            if nl < 0:
                break
            i = nl + 1
            continue
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("\\abstract{...} 未闭合，无法定位 Summary。")


def locate_region_cumcm(text):
    """返回 (body_start, body_end, suffix_idx) 字符下标。逻辑与原行号边界一致。"""
    lines = text.splitlines(keepends=True)

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

    mp_rel = next(
        (i for i in range(kw_rel - 1, -1, -1) if MINIPAGE_BEGIN_RE.search(region_lines[i])),
        None,
    )
    if mp_rel is None:
        raise ValueError("关键词行之前未找到 \\begin{minipage}，摘要正文边界不唯一。")

    body_start = region_start + mp_rel + 1
    body_end = region_start + kw_rel
    return (
        _line_offset(text, body_start),
        _line_offset(text, body_end),
        _line_offset(text, body_end),
    )


def locate_region_shuwei_en(text):
    """Summary 正文 = \\abstract{...} 内、\\label{abstract:end} 或闭合括号之前。"""
    m = ABSTRACT_CMD_RE.search(text)
    if m is None:
        raise ValueError("shuwei_en 未找到 \\abstract{...}，无法定位 Summary。")
    open_brace = m.end() - 1
    close_brace = _matching_brace(text, open_brace)
    body_start = open_brace + 1

    inner = text[body_start:close_brace]
    label_m = ABSTRACT_END_LABEL_RE.search(inner)
    if label_m is not None:
        body_end = body_start + label_m.start()
    else:
        body_end = close_brace

    kw_m = KEYWORDS_CMD_RE.search(text)
    if kw_m is None:
        raise ValueError("shuwei_en 未找到 \\keywords{...}，无法定位 Summary 结尾。")

    suffix = body_end
    return body_start, body_end, suffix


def locate_region(text, profile="cumcm"):
    """返回 (body_start, body_end, suffix_idx) 字符下标。找不到抛 ValueError。"""
    if profile == "shuwei_en":
        return locate_region_shuwei_en(text)
    return locate_region_cumcm(text)


def strip_tex(text: str) -> str:
    """近似纯文本化用于篇幅/数字统计：删注释、保留数学与宏参数内容。"""
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = text.replace("{", " ").replace("}", " ").replace("\\", " ")
    return text


def _line_no(text, offset):
    return text[:offset].count("\n") + 1


def command_locate(args) -> int:
    try:
        text = read_text(Path(args.paper))
        profile = resolve_contest_profile(args.contest_profile, args.paper)
        b0, b1, _ = locate_region(text, profile)
        body = text[b0:b1].strip()
        print(json.dumps({
            "contest_profile": profile,
            "body_start_line": _line_no(text, b0),
            "body_end_line": _line_no(text, b1),
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
        profile = resolve_contest_profile(args.contest_profile, args.original)
        o0, o1, os_ = locate_region(orig, profile)
        r0, r1, rs_ = locate_region(rev, profile)
        failures = []
        if orig[:o0] != rev[:r0]:
            failures.append("摘要正文之前的内容发生变化")
        if orig[os_:] != rev[rs_:]:
            failures.append("关键词行及之后的内容发生变化")
        if orig[o0:o1] == rev[r0:r1]:
            failures.append("摘要正文未发生变化")
        if failures:
            print(json.dumps({"passed": False, "contest_profile": profile,
                              "failures": failures}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({
            "passed": True,
            "contest_profile": profile,
            "original_body_chars": len(orig[o0:o1].strip()),
            "revised_body_chars": len(rev[r0:r1].strip()),
            "outside_abstract_identical": True,
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


def _audit_paragraphs(body, problems):
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    num_pat = re.compile(r"\d+(?:\.\d+)?|\\?%")
    for i, p in enumerate(paras[1:], start=2):
        if not num_pat.search(strip_tex(p)):
            problems.append(("WARN", "段落无量化",
                             f"第 {i} 段无任何数字——疑似有方法无结果（审计六型之 1/2），人工核查"))


def command_audit(args) -> int:
    problems = []
    try:
        text = read_text(Path(args.paper))
        profile = resolve_contest_profile(args.contest_profile, args.paper)
        b0, b1, _ = locate_region(text, profile)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    body = text[b0:b1]
    plain = strip_tex(body)

    if profile == "shuwei_en":
        n_words = len(re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)?", plain))
        if n_words < SHUWEI_EN_WORD_FLOOR:
            problems.append((
                "WARN", "摘要篇幅",
                f"Summary 约 {n_words} 词 < {SHUWEI_EN_WORD_FLOOR}——"
                f"疑似信息不足（不套国一中文字符窗；硬约束仍是一页）",
            ))
        _audit_paragraphs(body, problems)
        kw_m = KEYWORDS_CMD_RE.search(text)
        if kw_m is None:
            problems.append(("WARN", "关键词缺失", "未找到 \\keywords"))
        else:
            close = _matching_brace(text, kw_m.end() - 1)
            inner = text[kw_m.end():close].strip()
            if not inner:
                problems.append(("WARN", "关键词缺失", "\\keywords 为空"))
    else:
        n_chars = len(re.sub(r"\s", "", plain))
        if n_chars < 772:
            problems.append(("WARN", "摘要篇幅",
                             f"纯文本 {n_chars} 字符 < 国一基准 P10(772)——疑似信息不足，审计门核查六型"))
        elif n_chars > 1294:
            problems.append(("WARN", "摘要篇幅",
                             f"纯文本 {n_chars} 字符 > 国一基准 P90(1294)——疑似冗长或有超页风险，人工裁定"))
        _audit_paragraphs(body, problems)
        after = text[b1:]
        kw_line = next((ln for ln in after.splitlines()[:8] if KEYWORDS_RE.search(ln)), None)
        if kw_line is not None and "textbf" not in kw_line:
            problems.append(("WARN", "关键词未加粗",
                             "关键词行未使用 \\textbf（惯例 二.33）；摘要正文其余部分禁止加粗"))

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
    cli_profile, argv = peel_profile(sys.argv[1:])
    args = build_parser().parse_args(argv)
    args.contest_profile = cli_profile
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
