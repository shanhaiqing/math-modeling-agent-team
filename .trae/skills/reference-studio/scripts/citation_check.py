#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
citation_check.py — 正文引用 ↔ 参考文献列表双向核对（reference-studio 对账通道）

补上惯例 一.22b「正文括注来源全量入列」的机器核验缺口。

用法：
    python citation_check.py <paper.tex> [--contest-profile=cumcm|shuwei_zh|shuwei_en]

检查项：
  [幽灵引用] 正文 \\cite{key} 但列表无此条目 → ERROR（编译必出 [?]，交付硬伤）
  [僵尸文献] 列表有条目但正文从未引用 → WARN（凑数嫌疑，删除或正文补引）
  [括注提点] 正文中文括注含 4 位年份但该行无 \\cite（如（国家统计局，2023））
             → WARN（疑似括注来源未入列，惯例 一.22b，人工逐条核对）
             shuwei_en：仅当括注内含汉字才提点，避免 (Author, 2023) 误报

--contest-profile 缺省时读 paper.tex 同目录或 cwd 的 pipeline_state.json；非法/缺失视为 cumcm。

列表来源：优先 thebibliography 环境 \\bibitem{key}，否则 \\bibliography{...}
指向的 .bib 文件。正文提取前剔除注释与 thebibliography 环境自身。

输出：控制台逐条（级别 [规则] 说明）+ 末尾 JSON 汇总行。
退出码：0 = 无 ERROR；1 = 有 ERROR；2 = 用法错误。
"""
import json
import re
import sys
from pathlib import Path

CITE_PAT = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\{([^}]+)\}")
BIBITEM_PAT = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}")
BIB_ENV_PAT = re.compile(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", re.S)
BIBFILE_PAT = re.compile(r"\\bibliography\{([^}]+)\}")
BIB_ENTRY_PAT = re.compile(r"@\w+\s*\{([^,]*),")
COMMENT_PAT = re.compile(r"(?<!\\)%.*")
# 中文括注内含 19xx/20xx 年份（疑似正文括注来源，惯例 一.22b）
PAREN_YEAR_PAT = re.compile(r"[（(][^（）()]{0,60}(?:19|20)\d{2}[^（）()]{0,30}[)）]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
EXCLUDE_ENV_PAT = re.compile(
    r"\\begin\{(thebibliography|lstlisting|verbatim)\}.*?\\end\{\1\}", re.S)

LEGAL_PROFILES = ("cumcm", "shuwei_zh", "shuwei_en")


def resolve_contest_profile(cli_value, tex_path):
    if cli_value:
        v = cli_value.strip().lower()
        return v if v in LEGAL_PROFILES else "cumcm"
    candidates = [Path(tex_path).parent / "pipeline_state.json", Path.cwd() / "pipeline_state.json"]
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


def peel_args(argv):
    profile = None
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--contest-profile="):
            profile = a.split("=", 1)[1].strip()
        elif a == "--contest-profile":
            if i + 1 >= len(argv):
                print("用法错误：--contest-profile 需要 cumcm|shuwei_zh|shuwei_en")
                sys.exit(2)
            profile = argv[i + 1].strip()
            i += 1
        elif a.startswith("-"):
            print(__doc__)
            sys.exit(2)
        else:
            positional.append(a)
        i += 1
    return profile, positional


def extract_cites(text):
    """正文 \\cite 的 key 集合（剔除注释/文献列表/代码环境；多 key 逗号拆分）。"""
    body = EXCLUDE_ENV_PAT.sub("", text)
    keys = set()
    for line in body.splitlines():
        line = COMMENT_PAT.sub("", line)
        for m in CITE_PAT.finditer(line):
            keys.update(k.strip() for k in m.group(1).split(",") if k.strip())
    return keys


def extract_bib_keys(text, tex_path):
    """参考文献列表的 key 集合（thebibliography 优先，.bib 兜底）。"""
    env = BIB_ENV_PAT.search(text)
    if env:
        return {m.group(1).strip() for m in BIBITEM_PAT.finditer(env.group(0))}
    m = BIBFILE_PAT.search(text)
    if m:
        bib = Path(tex_path).parent / (m.group(1) + ".bib")
        if bib.is_file():
            bib_text = bib.read_text(encoding="utf-8", errors="replace")
            return {k.strip() for k in BIB_ENTRY_PAT.findall(bib_text)}
    return set()


def check_paren_sources(text, profile="cumcm"):
    """正文中文括注含年份但无 \\cite → WARN 提点（惯例 一.22b）。
    shuwei_en 只保留括注内含汉字的提点，跳过 (Author, 2023)。"""
    body = EXCLUDE_ENV_PAT.sub("", text)
    findings = []
    for i, line in enumerate(body.splitlines(), 1):
        line = COMMENT_PAT.sub("", line)
        if CITE_PAT.search(line):
            continue
        for m in PAREN_YEAR_PAT.finditer(line):
            span = m.group(0)
            if profile == "shuwei_en" and not CJK_RE.search(span):
                continue
            findings.append(("WARN", "括注提点",
                             f"第{i}行: 括注 '{span[:40]}' 含年份但无 \\cite——"
                             f"疑似括注来源未入列（惯例 一.22b），人工核对"))
    return findings[:10]


def main():
    profile_cli, positional = peel_args(sys.argv[1:])
    if len(positional) != 1:
        print(__doc__)
        sys.exit(2)
    tex_path = Path(positional[0])
    if not tex_path.is_file():
        print(f"用法错误：文件不存在 {positional[0]}")
        sys.exit(2)
    profile = resolve_contest_profile(profile_cli, tex_path)
    text = tex_path.read_text(encoding="utf-8", errors="replace")

    cites = extract_cites(text)
    bib_keys = extract_bib_keys(text, tex_path)

    findings = []
    ghosts = sorted(cites - bib_keys)
    zombies = sorted(bib_keys - cites)
    for k in ghosts:
        findings.append(("ERROR", "幽灵引用",
                         f"正文 \\cite{{{k}}} 但参考文献列表无此条目——编译必出 [?]，须补条目或删引用"))
    for k in zombies:
        findings.append(("WARN", "僵尸文献",
                         f"列表条目 '{k}' 正文从未引用——删除或正文补引（禁堆列表凑数）"))
    findings += check_paren_sources(text, profile)

    if not findings:
        print(f"PASS [双向一致] 正文引用 {len(cites)} 个 key ↔ 列表 {len(bib_keys)} 条，完全对应")
    for lv, rule, msg in findings:
        print(f"{lv} [{rule}] {msg}")
    n_err = sum(1 for lv, _, _ in findings if lv == "ERROR")
    n_warn = sum(1 for lv, _, _ in findings if lv == "WARN")
    print(json.dumps({"checker": "citation_check", "target": str(tex_path),
                      "contest_profile": profile,
                      "cite_keys": len(cites), "bib_keys": len(bib_keys),
                      "ghosts": len(ghosts), "zombies": len(zombies),
                      "errors": n_err, "warns": n_warn}, ensure_ascii=False))
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
