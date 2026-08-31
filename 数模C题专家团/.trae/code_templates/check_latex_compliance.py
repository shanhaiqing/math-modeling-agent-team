#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_latex_compliance.py — 论文 LaTeX 合规校验器（机查版）

把以下判据从"靠注意力执行的 prompt 检查"转为确定性机器检查：
  [合规] AGENTS.md "合规检查"节 + reviewer C 题核查第 8 项 COMPLIANCE-FAIL
        —— 无目录 / 不用 \\maketitle / 匿名性 / 附录可运行代码 / 页数提示
        prompt 位置：.trae/agents/paper-writer.md "篇幅与合规红线"节 + "LaTeX 格式规范"节
  [结构] paper-writer S4 层 1 —— 10 项结构、参考文献 ≥10、图表 ≥6、摘要要素
        prompt 位置：.trae/agents/paper-writer.md "论文结构"节 + S4 层 1
  [惯例] papers/国赛公开惯例.md 二.9/二.10/二.16/二.22 —— 摘要页三件套、推导回避表述、AI 高频词、标题编号样式
        prompt 位置：.trae/agents/paper-writer.md "LaTeX 格式规范"节（标题编号样式指针）
  [一.22a] papers/国赛公开惯例.md 一.22(a) —— 参考文献年份比对（A2a 机查项，历年校准反馈）
        提取 \bibitem/.bib 条目年份，不得晚于赛题发布日期；--contest-year=YYYY 启用，
        未提供 → WARN 提示；晚于赛题年份 → ERROR（时代错位）
        prompt 位置：.trae/agents/independent-reviewer.md C 题核查 #8 来源子项（指针至惯例一.22）
  [二.16b] papers/国赛公开惯例.md 二.16 —— 内部高频短语（≥5 次）与超长段落（>300 字）自查
        （W-4 机查化，历年校准反馈，WARN 项；正文统计，排除附录与各浮动体/代码环境）
        prompt 位置：.trae/agents/paper-writer.md 去 AI 味自查（S4/阶段 5 自审）

同步维护条款（T-1）：新增或修改机查项时，须同步核对对应 agent prompt 是否已下达该要求。
机查要求集不得超出 prompt 要求集（详见 .trae/papers/国赛公开惯例.md 五.2）。
本轮即时整改（历年评审复核）：排版节 check_visual_style 检出的 WARN（"未检出一级标题
'一、'编号配置"）已通过 paper-writer.md LaTeX 格式规范节补指针 + 国赛公开惯例.md 二.22
明确推荐样式同步对齐。

用法:
  python check_latex_compliance.py <paper.tex路径> [project代码目录] [paper.pdf路径] [--contest-year=YYYY]

退出码: 0 = 无 ERROR（可有 WARN）；1 = 存在 ERROR；2 = 用法/读取错误
输出:   控制台逐条打印 + 在 paper.tex 同目录写 latex_compliance_report.json
分级:   ERROR = 必须修复（阻塞提交/进入下一阶段）；WARN = 需人工判定；PASS = 通过
"""
import difflib
import json
import re
import sys
from pathlib import Path

FINDINGS = []


def error(rule, loc, msg):
    FINDINGS.append({"level": "ERROR", "rule": rule, "location": loc, "message": msg})


def warn(rule, loc, msg):
    FINDINGS.append({"level": "WARN", "rule": rule, "location": loc, "message": msg})


def ok(rule, msg):
    FINDINGS.append({"level": "PASS", "rule": rule, "location": "", "message": msg})


# ---------- 预处理 ----------

def strip_comments(text):
    """去除未被转义的 % 注释（保留行号结构）。"""
    out = []
    for line in text.splitlines():
        res, i = [], 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            res.append(line[i])
            i += 1
        out.append("".join(res))
    return "\n".join(out)


def extract_env(text, env):
    """提取指定环境的内容列表。"""
    pat = re.compile(r"\\begin\{" + re.escape(env) + r"\}(.*?)\\end\{" + re.escape(env) + r"\}", re.S)
    return pat.findall(text)


# ---------- 检查 1：目录 / maketitle / author / date ----------

def check_toc_maketitle(text):
    for i, line in enumerate(text.splitlines(), 1):
        if "\\tableofcontents" in line:
            error("合规", f"第{i}行", "检测到 \\tableofcontents——官方明确'不要目录'，必须删除")
        if "\\maketitle" in line:
            error("合规", f"第{i}行", "检测到 \\maketitle——会带入队名/日期，摘要页须改用 center 排版标题")
    m = re.search(r"\\author\{([^}]+)\}", text)
    if m and m.group(1).strip():
        warn("合规", "", f"\\author 含内容（{m.group(1).strip()[:30]!r}）——匿名性风险，请人工确认未泄露身份")
    m = re.search(r"\\date\{([^}]+)\}", text)
    if m and m.group(1).strip():
        warn("合规", "", f"\\date 含内容（{m.group(1).strip()[:30]!r}）——摘要页不得出现日期，请人工确认")
    if not any(f["rule"] == "合规" and f["level"] == "ERROR" for f in FINDINGS):
        ok("合规", "无目录、无 \\maketitle")


# ---------- 检查 1b：排版颜值（对标真实国赛 Word 论文） ----------

def check_visual_style(text):
    """真实国赛论文视觉惯例（对标真实获奖论文固化）：
    页脚居中页码无页眉 / 一级标题'一、'黑三居中 / 宽行距。"""
    if not re.search(r"\\pagestyle\{plain\}|\\fancypagestyle|\\fancyfoot", text):
        warn("排版", "", "未检出 \\pagestyle{plain} 或 fancyhdr 页脚设置——ctexart 默认 headings 会产生页眉+右上角页码，与真实论文（页脚居中、无页眉）不符")
        return
    if re.search(r"name\s*=\s*\{[^}]*、", text):
        ok("排版", "页码/标题体系已按国赛颜值惯例配置")
    else:
        warn("排版", "", "未检出一级标题'一、'编号配置（ctexset name={,、}）——真实论文一级标题为'一、 xxx'黑体三号居中，请人工确认标题风格")


# ---------- 检查 2：结构 10 项 ----------

STRUCTURE = [
    ("摘要", re.compile(r"摘要|\\begin\{abstract\}"), "ERROR"),
    ("问题重述", re.compile(r"问题重述"), "WARN"),
    ("问题分析", re.compile(r"问题分析"), "WARN"),
    ("模型假设", re.compile(r"模型假设|模型的假设"), "WARN"),
    ("符号说明", re.compile(r"符号说明|符号表|符号约定"), "WARN"),
    ("模型的建立与求解", re.compile(r"模型的建立与求解|模型建立与求解|建立与求解|建模与求解|模型的建立|模型建立|模型构建|模型求解"), "ERROR"),
    ("灵敏度与误差分析", re.compile(r"灵敏度|敏感性"), "WARN"),
    ("模型评价", re.compile(r"模型评价|评价与推广|模型的评价"), "WARN"),
    ("参考文献", re.compile(r"参考文献|thebibliography|bibliography"), "ERROR"),
    ("附录", re.compile(r"\\appendix|附录"), "ERROR"),
]


def check_structure(text):
    # 先剥掉 \hspace{...} 等间距命令，使 "摘\hspace{2em}要" 等写法可匹配
    text = re.sub(r"\\hspace\{[^}]*\}", "", text)
    missing_err, missing_warn = [], []
    for name, pat, sev in STRUCTURE:
        if not pat.search(text):
            (missing_err if sev == "ERROR" else missing_warn).append(name)
    if missing_err:
        error("结构", "", f"缺关键结构节: {', '.join(missing_err)}")
    if missing_warn:
        warn("结构", "", f"未检出以下结构节（可能为命名变体，请人工确认）: {', '.join(missing_warn)}")
    if not missing_err and not missing_warn:
        ok("结构", "结构 10 项全部检出")


# ---------- 检查 3：摘要要素 ----------

def check_abstract(text):
    text = re.sub(r"\\hspace\{[^}]*\}", "", text)
    m = re.search(r"关键词[}\s]*[:：]([^\n]+)", text) or re.search(r"关键字[}\s]*[:：]([^\n]+)", text)
    if not m:
        warn("摘要", "", "未检出'关键词：'行——摘要页须含关键词 3-5 个")
    else:
        line = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{)?", "", m.group(1))
        line = line.replace("}", "")
        kws = [k for k in re.split(r"[;；,，、\s]+", line.strip().rstrip("。.")) if k]
        if not (3 <= len(kws) <= 5):
            warn("摘要", "", f"关键词数量 {len(kws)} 个，不在 3-5 个范围内: {kws}")
        else:
            ok("摘要", f"关键词 {len(kws)} 个 ✓")
    # 摘要长度代理：'摘要'标题（或 abstract 环境）到 '关键词' 之间的字符数
    m1 = re.search(r"摘要", text) or re.search(r"\\begin\{abstract\}", text)
    if m1 and m:
        body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", "", text[m1.end():m.start()])
        body = re.sub(r"[{}$\s\\]", "", body)
        n = len(body)
        if n < 400:
            warn("摘要", "", f"摘要正文约 {n} 字 < 400 字下限（代理估算，请人工复核）")
        elif n > 900:
            warn("摘要", "", f"摘要正文约 {n} 字 > 800 字上限（代理估算；官方硬约束为 ≤1 页，请人工复核）")
        else:
            ok("摘要", f"摘要正文约 {n} 字（400-800 区间内）")


# ---------- 检查 4：参考文献 ≥10 ----------

def check_bibliography(text, tex_path):
    n = len(re.findall(r"\\bibitem", text))
    if n == 0:
        m = re.search(r"\\bibliography\{([^}]+)\}", text)
        if m:
            bib = tex_path.parent / (m.group(1) + ".bib")
            if bib.is_file():
                n = len(re.findall(r"@\w+\s*\{", bib.read_text(encoding="utf-8", errors="ignore")))
            else:
                warn("参考文献", "", f"声明了 {m.group(1)}.bib 但文件不存在")
                return
    if n == 0:
        error("参考文献", "", "未检出任何参考文献条目（要求 ≥10 篇）")
    elif n < 10:
        warn("参考文献", "", f"参考文献 {n} 篇 < 10 篇")
    else:
        ok("参考文献", f"参考文献 {n} 篇 ≥10 ✓")


# ---------- 检查 5：图表数量与引用 ----------

def check_figures(text):
    n_img = len(re.findall(r"\\includegraphics", text))
    n_ref = len(re.findall(r"\\ref\{", text))
    if n_img < 6:
        error("图表", "", f"\\includegraphics 仅 {n_img} 处 < 6 张下限（S4 层 1 第 13 项：图数 <6 → BLOCKED）")
    else:
        ok("图表", f"\\includegraphics {n_img} 处 ≥6 ✓")
    if n_ref == 0:
        warn("图表", "", "未检出 \\ref{} 交叉引用——图表公式须有 \\ref{} 引用")
    elif n_ref < 6:
        warn("图表", "", f"\\ref{{}} 仅 {n_ref} 处，交叉引用偏少，请人工确认每图均被引用")
    else:
        ok("图表", f"\\ref{{}} {n_ref} 处 ✓")


# ---------- 检查 6：推导回避表述 ----------

def check_avoidance(text):
    pat_err = re.compile(r"推导较为复杂|推导从略|限于篇幅[^。]{0,20}推导|推导过程从略|此处省略.{0,6}推导")
    pat_warn = re.compile(r"不再赘述|限于篇幅|此处从略|过程从略")
    hits_err = [(i + 1, m.group(0)) for i, line in enumerate(text.splitlines()) if (m := pat_err.search(line))]
    hits_warn = [(i + 1, m.group(0)) for i, line in enumerate(text.splitlines()) if (m := pat_warn.search(line))]
    for ln, w in hits_err:
        error("推导", f"第{ln}行", f"检出回避性表述 '{w}'——推导必须内联正文完整呈现")
    for ln, w in hits_warn[:3]:
        warn("推导", f"第{ln}行", f"检出疑似回避表述 '{w}'——请人工确认未回避必要推导")
    if not hits_err:
        ok("推导", "无推导回避性表述")


# ---------- 检查 7：AI 高频词（惯例 二.16） ----------

AI_WORDS = ["此外", "另外", "关键的", "深入探讨", "具有重要意义", "充分展示"]
AI_PATTERNS = [
    ("为...奠定基础", re.compile(r"为.{0,8}奠定基础")),
    ("不仅...而且...", re.compile(r"不仅[^。]{0,40}而且")),
    ("尽管...仍面临挑战", re.compile(r"尽管[^。]{0,40}仍面临挑战")),
    ("未来研究可以...", re.compile(r"未来研究可以")),
]


def check_ai_words(text):
    hits = {}
    for w in AI_WORDS:
        c = text.count(w)
        if c:
            hits[w] = c
    for name, pat in AI_PATTERNS:
        c = len(pat.findall(text))
        if c:
            hits[name] = c
    if hits:
        detail = ", ".join(f"'{w}'×{c}" for w, c in sorted(hits.items(), key=lambda x: -x[1]))
        warn("AI味", "", f"检出 AI 高频词/句型（惯例 二.16 黑名单）: {detail}")
    else:
        ok("AI味", "无 AI 高频词")


# ---------- 检查 8：匿名性关键词扫描 ----------

IDENTITY_WORDS = ["大学", "学院", "学校", "队员", "指导教师", "教练", "赛区", "学号", "队号", "参赛队"]


def check_anonymity(text):
    # 排除参考文献环境（出版社常含大学名）
    bib = extract_env(text, "thebibliography")
    scan_text = text
    for b in bib:
        scan_text = scan_text.replace(b, "")
    hits = {}
    for i, line in enumerate(scan_text.splitlines(), 1):
        for w in IDENTITY_WORDS:
            if w in line:
                hits.setdefault(w, []).append(i)
    if hits:
        detail = "; ".join(f"'{w}' 第{v[:3]}行" + ("..." if len(v) > 3 else "") for w, v in hits.items())
        warn("匿名", "", f"检出身份敏感词（已排除参考文献，需人工逐处确认非身份信息）: {detail}")
    else:
        ok("匿名", "全文（除参考文献）无身份敏感词")


# ---------- 检查 9：附录代码与 project/ 一致性 ----------

def norm_code(s):
    return "\n".join(l.rstrip() for l in s.splitlines() if l.strip() and not l.strip().startswith("#"))


def check_appendix_code(text, tex_path, project_dir):
    has_appendix = bool(re.search(r"\\appendix|附录", text))
    listings = extract_env(text, "lstlisting")
    inputs = re.findall(r"\\lstinputlisting(?:\[[^\]]*\])?\{([^}]+)\}", text)
    # fancyvrb 的 \VerbatimInput 与 \lstinputlisting 等效（直接引用源文件）
    inputs += re.findall(r"\\VerbatimInput(?:\[[^\]]*\])?\{([^}]+)\}", text)
    if not has_appendix:
        return  # 结构检查已报缺附录
    if not listings and not inputs:
        error("附录代码", "", "附录存在但未检出任何代码（lstlisting/\\lstinputlisting/\\VerbatimInput）——附录含完整可运行源程序是官方硬约束")
        return
    # lstinputlisting 指向的文件存在性
    for rel in inputs:
        target = (tex_path.parent / rel).resolve()
        if not target.is_file():
            # 也尝试相对 project 目录解析
            if project_dir and (Path(project_dir) / rel).is_file():
                continue
            error("附录代码", rel, f"\\lstinputlisting 引用的文件不存在: {rel}")
    py_files = list(Path(project_dir).rglob("*.py")) if project_dir else []
    if project_dir and not py_files:
        warn("附录代码", "", f"project 目录 {project_dir} 下未找到 .py 文件，一致性比对降级为存在性检查")
    big_blocks = [b for b in listings if len([l for l in b.splitlines() if l.strip()]) >= 5]
    if listings and not big_blocks:
        warn("附录代码", "", f"附录含 {len(listings)} 个代码块但均 <5 行，跳过一致性比对——请人工确认附录含完整可运行源程序")
        return
    if big_blocks and not py_files:
        warn("附录代码", "", f"附录含 {len(big_blocks)} 个内联代码块但未提供可比对的 project/*.py——请人工确认与 project/ 实际代码逐行一致（推荐改用 \\lstinputlisting 直接引用）")
        return
    for idx, block in enumerate(big_blocks, 1):
        nb = norm_code(block)
        nbc = re.sub(r"\s+", "", nb)
        best, best_f = 0.0, None
        for pf in py_files:
            try:
                src = norm_code(pf.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            srcc = re.sub(r"\s+", "", src)
            sm = difflib.SequenceMatcher(None, nbc, srcc)
            ratio = sm.ratio()
            # 子集分：块是长文件的一部分时，全长 ratio 会被低估，
            # 用匹配块总长度 / 块长度衡量"块内容的被覆盖率"
            subset = sum(m.size for m in sm.get_matching_blocks()) / max(len(nbc), 1)
            r = max(ratio, subset)
            if r > best:
                best, best_f = r, pf.name
        if best >= 0.90:
            ok("附录代码", f"代码块{idx} 与 {best_f} 一致（相似度 {best:.0%}）")
        elif best >= 0.60:
            warn("附录代码", f"代码块{idx}", f"与最相近文件 {best_f} 相似度仅 {best:.0%}——请人工确认非'示意性改写'")
        else:
            error("附录代码", f"代码块{idx}", f"与 project/ 全部 .py 最高相似度 {best:.0%}——疑似示意性改写（附录代码必须与 project/ 实际代码一致）")
    if inputs and not big_blocks:
        ok("附录代码", f"附录代码通过 \\lstinputlisting/\\VerbatimInput 直接引用 {len(inputs)} 个文件 ✓")


# ---------- 检查 10：页数（PDF 代理） ----------

def check_pages(tex_path, pdf_path):
    pdf = Path(pdf_path) if pdf_path else tex_path.with_suffix(".pdf")
    if not pdf.is_file():
        warn("页数", "", "未找到编译后 PDF——正文页数（≥10 且尽量 ≤28）需编译后人工核对")
        return
    try:
        from pypdf import PdfReader
        n = len(PdfReader(str(pdf)).pages)
        warn("页数", "", f"PDF 共 {n} 页（含附录）。正文（摘要页后、附录前）须 ≥10 且尽量 ≤28——附录起止页需人工核对后判定")
    except Exception as e:
        warn("页数", "", f"PDF 页数读取失败（{e}）——请人工核对正文页数")


# ---------- 检查 11：参考文献年份比对（A2a，惯例 一.22a） ----------

YEAR_PAT = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


def _bib_entries(text, tex_path):
    """提取参考文献条目 [(key, 条目文本)]：优先 thebibliography 环境，其次 .bib 文件。"""
    entries = []
    for env in extract_env(text, "thebibliography"):
        for m in re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}(.*?)(?=\\bibitem|\Z)", env, re.S):
            entries.append((m.group(1), m.group(2)))
    if not entries:
        m = re.search(r"\\bibliography\{([^}]+)\}", text)
        if m:
            bib = tex_path.parent / (m.group(1) + ".bib")
            if bib.is_file():
                bib_text = bib.read_text(encoding="utf-8", errors="ignore")
                for em in re.finditer(r"@\w+\s*\{([^,]*),(.*?)(?=@\w+\s*\{|\Z)", bib_text, re.S):
                    entries.append((em.group(1), em.group(2)))
    return entries


def check_reference_years(text, tex_path, contest_year):
    entries = _bib_entries(text, tex_path)
    if not entries:
        return  # 参考文献存在性已由 check_bibliography 报告
    if contest_year is None:
        warn("来源年份", "", f"未提供 --contest-year=YYYY——{len(entries)} 条文献年份无法机查比对，"
                            f"请人工核对发表年份均不晚于赛题发布年份（惯例 一.22a）")
        return
    late, n_year = [], 0
    for key, body in entries:
        years = [int(y) for y in YEAR_PAT.findall(body)]
        if not years:
            continue
        n_year += 1
        y = max(years)  # 条目内最晚年份作为发表年份候选（含再版/卷期年）
        if y > contest_year:
            late.append((key, y))
    if late:
        detail = "; ".join(f"{k}({y})" for k, y in late[:8])
        more = f" 等 {len(late)} 条" if len(late) > 8 else ""
        error("来源年份", "", f"{len(late)} 条参考文献年份晚于赛题发布年份 {contest_year}: {detail}{more}"
                            f"——时代错位，须替换为赛题日期前的等价来源（惯例 一.22a）")
    else:
        ok("来源年份", f"{n_year} 条可提取年份的文献均 ≤ {contest_year} ✓")


# ---------- 检查 12：内部高频短语与超长段落（C4，惯例 二.16b，W-4 机查化） ----------

EXCLUDE_ENVS = ("figure", "table", "lstlisting", "verbatim", "equation", "equation*",
                "align", "align*", "gather", "gather*", "multline", "multline*",
                "thebibliography", "abstract")
ENV_PAT = re.compile(r"\\begin\{(" + "|".join(EXCLUDE_ENVS) + r")\}.*?\\end\{\1\}", re.S)
CJK_RUN = re.compile(r"[一-鿿]+")
LONG_PARA_THRESHOLD = 300


def _main_body_lines(text):
    """正文行列表 (行号, 行文本)：切除 \\appendix 之后内容，剔除浮动体/代码环境（保留行号结构）。"""
    cut = text.find("\\appendix")
    if cut >= 0:
        text = text[:cut]
    text = ENV_PAT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return [(i, line) for i, line in enumerate(text.splitlines(), 1)]


def _strip_tex(s):
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", "", s)
    return re.sub(r"[{}\s$\\]", "", t)


def check_repetition_paragraphs(text):
    lines = _main_body_lines(text)
    # (a) 内部高频短语：连续中文串内 n-gram（n=4..12）计数 ≥5，保留极大短语
    runs = [rm.group(0) for _, line in lines for rm in CJK_RUN.finditer(line)]
    counts = {}
    for run in runs:
        L = len(run)
        for n in range(4, min(12, L) + 1):
            for s in range(L - n + 1):
                g = run[s:s + n]
                counts[g] = counts.get(g, 0) + 1
    freq = {g: c for g, c in counts.items() if c >= 5}
    maximal = [(g, c) for g, c in freq.items()
               if not any(g != h and g in h and freq[h] == c for h in freq)]
    # 剔除静态黑名单已覆盖者（check_ai_words 负责），仅报黑名单之外的自造短语
    maximal = [(g, c) for g, c in maximal if not any(w in g for w in AI_WORDS)]
    maximal.sort(key=lambda x: (-x[1], -len(x[0])))
    if maximal:
        detail = "; ".join(f"'{g}'×{c}" for g, c in maximal[:8])
        more = f" 等 {len(maximal)} 个" if len(maximal) > 8 else ""
        warn("AI味", "", f"内部高频短语（≥5 次，惯例 二.16b）: {detail}{more}"
                        f"——请人工判定是否需将部分实例替换为具体指代或近义表述")
    else:
        ok("AI味", "无 ≥5 次的内部高频四字及以上自造短语")
    # (b) 超长段落：空行分段，去 LaTeX 命令后统计字数
    paras, cur, start = [], [], None
    for ln, line in lines:
        if line.strip():
            if start is None:
                start = ln
            cur.append(line)
        elif cur:
            paras.append((start, "\n".join(cur)))
            cur, start = [], None
    if cur:
        paras.append((start, "\n".join(cur)))
    long_ps = [(st, len(_strip_tex(p))) for st, p in paras]
    long_ps = [(st, n) for st, n in long_ps if n > LONG_PARA_THRESHOLD]
    if long_ps:
        detail = "; ".join(f"第{st}行起约{n}字" for st, n in long_ps[:6])
        more = f" 等 {len(long_ps)} 段" if len(long_ps) > 6 else ""
        warn("AI味", "", f"超长段落（>{LONG_PARA_THRESHOLD} 字，惯例 二.16b）: {detail}{more}——请拆分或记录理由")
    else:
        ok("AI味", f"无超过 {LONG_PARA_THRESHOLD} 字的超长段落")


# ---------- 主流程 ----------

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(2)
    contest_year, positional = None, []
    for a in argv:
        if a.startswith("--contest-year="):
            try:
                contest_year = int(a.split("=", 1)[1].strip())
            except ValueError:
                print(f"✗ --contest-year 参数无法解析: {a!r}，应为 --contest-year=YYYY")
                sys.exit(2)
        elif not a.startswith("--"):
            positional.append(a)
    if not positional:
        print(__doc__)
        sys.exit(2)
    tex_path = Path(positional[0])
    project_dir = positional[1] if len(positional) > 1 else None
    pdf_path = positional[2] if len(positional) > 2 else None
    if not tex_path.is_file():
        print(f"✗ 文件不存在: {tex_path}")
        sys.exit(2)
    raw = tex_path.read_text(encoding="utf-8", errors="ignore")
    text = strip_comments(raw)

    check_toc_maketitle(text)
    check_visual_style(text)
    check_structure(text)
    check_abstract(text)
    check_bibliography(text, tex_path)
    check_reference_years(text, tex_path, contest_year)
    check_figures(text)
    check_avoidance(text)
    check_ai_words(text)
    check_repetition_paragraphs(text)
    check_anonymity(text)
    check_appendix_code(text, tex_path, project_dir)
    check_pages(tex_path, pdf_path)

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    n_warn = sum(1 for f in FINDINGS if f["level"] == "WARN")
    n_pass = sum(1 for f in FINDINGS if f["level"] == "PASS")

    icon = {"ERROR": "✗", "WARN": "⚠", "PASS": "✓"}
    for f in FINDINGS:
        loc = f" {f['location']}" if f["location"] else ""
        print(f"{icon[f['level']]} {f['level']:<5} [{f['rule']}]{loc} {f['message']}")
    print(f"\n汇总: {n_err} ERROR / {n_warn} WARN / {n_pass} PASS")

    report = {"target": str(tex_path),
              "summary": {"ERROR": n_err, "WARN": n_warn, "PASS": n_pass},
              "findings": FINDINGS}
    out = tex_path.parent / "latex_compliance_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已写入: {out}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
