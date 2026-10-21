#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_reflection.py — 反思日志反敷衍机查（WARN 级，不阻塞）

[契约] AGENTS.md 质量红线节（原仅验"5 份 decision_logs 存在"）+ 红队自查机制节
[背景] 双模型评审共识 C1 / 场景 B（P0）：红线只验文件存在，agent 写一份格式完美、
       逐项 ✓、依据栏填"已逐项核对"的日志即可全链路绿灯；禁止敷衍的禁令其执行者
       与被禁者是同一 LLM，违规零成本。本脚本给敷衍行为留下可检测痕迹。
[定位] **WARN 级，不阻塞流水线**——脚本只能识别"疑似敷衍"的形式特征，无法判断
       检查是否真做；裁定权按惯例 五.1 归下游独立角色（reviewer）。
[分工] check_pipeline_manifest.py 查"日志在不在"；本脚本查"日志是否空洞"。

检查项（对 s1/s2/s3/s4_reflection.md 逐个执行）：
  R1 套话密度：黑名单短语命中数 ≥3 → WARN
  R2 全 ✓ 无警示：✓ 计数 ≥5 且 ⚠️/✗ 计数为 0 → WARN（层 1 逐项扫描应有区分度）
  R3 空依据：✓/⚠️/✗ 标记后 40 字符内无任何实质内容 → WARN
  R4 依据过短：标记后内容 <20 字符且不含数字/文件名 → WARN
  R5 红队节空洞：层 3 缺"搜查对象/搜查范围"清单，或声称 0 个 high severity
     却无对象清单 → WARN
  R6 篇幅异常：正文（去空白）<300 字符 → WARN

用法：
  python check_reflection.py <项目根> [--report 路径] [--strict]
  --strict  把 WARN 提升为 ERROR（默认关闭；仅在用户明确要求硬门时启用）
  默认仅终端输出，需留证时 --report 写入 decision_logs/reflection_check_report.json

退出码: 0 = 无 WARN/ERROR；1 = 存在 WARN（--strict 时为 ERROR）；2 = 用法错误
"""
import argparse
import json
import re
import sys
from pathlib import Path

REFLECTION_FILES = ["s1_reflection.md", "s2_reflection.md", "s3_reflection.md", "s4_reflection.md"]

# 套话黑名单：无信息量的自我背书表述（AGENTS.md 禁止行为的机查化）
BOILERPLATE = [
    "已检查", "无问题", "均符合", "已逐项核对", "全部通过", "符合要求",
    "没有问题", "一切正常", "均已核对", "检查完毕", "无异常", "已确认无误",
]

# ✓ 标记后实质内容的判据：含数字或文件/字段引用即视为有依据
EVIDENCE_HINT = re.compile(r"\d|\.json|\.py|\.md|\.tex|§|惯例|第\s*\d+|行\s*\d+")

FINDINGS = []


def warn(item, msg):
    FINDINGS.append({"level": "WARN", "item": item, "msg": msg})


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return None


def split_layers(text):
    """按"层 1 / 层 2 / 层 3"切分；无标记时返回全文作为单一块。"""
    marks = list(re.finditer(r"层\s*([123])", text))
    layers = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        layers.setdefault(m.group(1), []).append(text[m.start():end])
    return {k: "\n".join(v) for k, v in layers.items()}


def collect_verdict_marks(text):
    """只收集【表格判定列】的标记，不解析散文行内标记。

    2026-09-10 三轮修复：
      第一轮：原实现用 finditer 数全文 ✓，把"P1 宽度 242.98/70=c_W=3.471 ✓"这类
              行内数值互印证标记计入判定，导致高质量日志被误判 R2「43 个 ✓」。
      第二轮：曾尝试识别散文判定行，但层 2/层 3 证据文本里大量出现
              "- 符号说明……三方一致 ✓"形态，其 ✓ 位于句末（后面本就无内容），
              被误判为 R3「空依据」。散文形式下两类 ✓ 无法可靠区分，故放弃散文解析。
      第三轮：表格判定列可能在【中间】也可能在【末列】。
              实测 s2 的「惯例一.11 参数逐字回读」表为 | 原文参数 | 代码位置与取值 | ✓ |，
              ✓ 在末列、证据在其前一格；原实现只取"✓ 后一格"为依据，导致该表 11 行
              被判「空依据」——而那实际是逐字回读 + 代码定位的高质量证据。

    现行判据：markdown 表格中【单元格内容恰为单个判定符号】即判定列；
      依据取「✓ 后一格」，若 ✓ 已在末列则取「前一格」。
    s1-s4 的层 1 按模板均为表格形式，S4 模板亦强制表格 + 「证据指针」列。
    行内 ✓（数值互印证）不参与判定统计，属正常证据书写。
    """
    verdicts = []  # [(mark, basis)]

    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        for idx, cell in enumerate(cells):
            if cell in ("✓", "✅", "⚠️", "✗", "❌"):
                if idx + 1 < len(cells):
                    basis = cells[idx + 1]          # 判定列在中间：依据在后一格
                else:
                    basis = cells[idx - 1] if idx > 0 else ""   # 判定列在末列：依据在前一格
                verdicts.append((cell, basis))
                break

    return verdicts


def has_verdict_table(text):
    """判断是否存在层 1 判定表格（含判定符号或模板占位符 ✓/⚠️/✗）。"""
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if any(c in ("✓", "✅", "⚠️", "✗", "❌", "✓/⚠️/✗") for c in cells):
            return True
    return False


def check_marks(text, fname):
    """R2/R3/R4：解析逐项标注与依据质量（仅表格判定列）。"""
    if not has_verdict_table(text):
        warn(fname, "R0 未检出层 1 判定表格：反思日志未按模板使用表格形式"
                    "（s4_reflection_template.md 规定层 1 为表格 + 证据指针列），"
                    "无法机查判定质量——请人工核对")
        return

    verdicts = collect_verdict_marks(text)

    n_ok = sum(1 for m, _ in verdicts if m in ("✓", "✅"))
    n_bad = sum(1 for m, _ in verdicts if m in ("⚠️", "✗", "❌"))

    # 全文标记总数仅用于消息中说明"另有行内验证标记"，不参与判定
    n_all_ok = text.count("✓") + text.count("✅")

    if n_ok >= 5 and n_bad == 0:
        # 全 ✓ 时先评估依据质量：依据充分则降为中性提示，不断言敷衍
        bases = [b for m, b in verdicts if m in ("✓", "✅") and b.strip()]
        avg_len = (sum(len(re.sub(r"[\s|]", "", b)) for b in bases) / len(bases)) if bases else 0
        ptr_hits = sum(1 for b in bases if EVIDENCE_HINT.search(b))
        ptr_ratio = (ptr_hits / len(bases)) if bases else 0
        extra = (f"；全文另有 {n_all_ok - n_ok} 个行内数值验证标记（属证据书写，不计入判定）"
                 if n_all_ok > n_ok else "")
        if avg_len >= 60 and ptr_ratio >= 0.7:
            warn(fname, f"R2 判定全 ✓ 无警示：{n_ok} 项判定全为 ✓、0 个 ⚠️/✗{extra}。"
                        f"但依据质量充分（平均 {avg_len:.0f} 字符、{ptr_ratio:.0%} 含证据指针），"
                        f"形式上不构成敷衍——层 1 全项通过本身偏离常态，请 reviewer 抽查 2 项证伪")
        else:
            warn(fname, f"R2 全 ✓ 无警示：{n_ok} 项判定全为 ✓、0 个 ⚠️/✗{extra}，"
                        f"且依据偏弱（平均 {avg_len:.0f} 字符、{ptr_ratio:.0%} 含证据指针）"
                        f"——疑为未真实展开（AGENTS.md 红队机制禁止无差别 ✓）")

    empty = short = 0
    for mark, basis in verdicts:
        cleaned = re.sub(r"[\s|：:，,。\-—*#`\[\]]", "", basis)
        if not cleaned:
            empty += 1
        elif len(cleaned) < 20 and not EVIDENCE_HINT.search(basis):
            short += 1
    if empty:
        warn(fname, f"R3 空依据 {empty} 处：表格判定列后的依据单元格为空——"
                    f"每个 ✓ 须附证据指针（文件+行号 / 机查报告条目号 / JSON 字段路径）")
    if short:
        warn(fname, f"R4 依据过短 {short} 处：<20 字符且无数字/文件引用，疑为占位")


def check_boilerplate(text, fname):
    """R1：套话密度。"""
    hits = {p: text.count(p) for p in BOILERPLATE if p in text}
    total = sum(hits.values())
    if total >= 3:
        detail = "、".join(f"{k}×{v}" for k, v in sorted(hits.items(), key=lambda x: -x[1])[:4])
        warn(fname, f"R1 套话密度 {total} 处（{detail}）——命中 AGENTS.md"
                    f"「不得写『已检查』『无问题』等模糊结论」禁令")


def check_redteam(text, fname):
    """R5：红队节空洞。"""
    layers = split_layers(text)
    rt = layers.get("3")
    if rt is None:
        m = re.search(r"(红队自查|层\s*3)([\s\S]*)", text)
        rt = m.group(2) if m else None
    if rt is None:
        warn(fname, "R5 未找到层 3 / 红队自查节——强制产出缺失")
        return
    has_scope = bool(re.search(r"搜查对象|搜查范围|对象清单|扫描范围|搜查清单", rt))
    zero_hs = bool(re.search(r"(0|零|无)\s*(个)?\s*high\s*severity|未发现\s*high", rt, re.I))
    if not has_scope:
        warn(fname, "R5 红队节缺「搜查范围与证据」（搜查对象清单 + 每对象检查结论）"
                    "——努力举证制要求书面记录搜查对象，无清单即无法证伪")
    elif zero_hs and len(rt.strip()) < 200:
        warn(fname, "R5 声称 0 个 high severity 且红队节篇幅 <200 字符——"
                    "凭搜查范围与证据记录判定通过，篇幅过短疑未真实搜查")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--report", default=None)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root)
    logdir = root / "decision_logs"
    if not logdir.is_dir():
        print(f"⚠ 未找到 {logdir}——尚未产生反思日志（建模阶段未开始属正常）")
        sys.exit(0)

    scanned = 0
    for name in REFLECTION_FILES:
        p = logdir / name
        if not p.is_file():
            continue
        scanned += 1
        text = read_text(p)
        if text is None:
            warn(name, "文件存在但读取失败（编码异常）")
            continue
        body = re.sub(r"\s", "", text)
        if len(body) < 300:
            warn(name, f"R6 篇幅异常：去空白后仅 {len(body)} 字符 <300，疑为占位文件")
        # R6 与其他检查叠加，不短路：敷衍日志常刻意写长伪装，篇幅正常不代表内容真实
        check_boilerplate(text, name)
        check_marks(text, name)
        check_redteam(text, name)

    if scanned == 0:
        print("⚠ decision_logs/ 下无 s1-s4_reflection.md——尚未产生反思日志")
        sys.exit(0)

    level = "ERROR" if args.strict else "WARN"
    for f in FINDINGS:
        f["level"] = level
    print(f"扫描 {scanned} 份反思日志，{len(FINDINGS)} 项 {level}：")
    for f in FINDINGS:
        print(f"  {f['level']:<5} [{f['item']}] {f['msg']}")
    if not FINDINGS:
        print("  全部通过：未检出套话堆积、全 ✓ 无警示、空依据或红队空洞特征")
    print(f"\n提示：本脚本只识别敷衍的形式特征，无法判断检查是否真做；"
          f"{level} 按惯例 五.1 交下游独立角色裁定，不自动阻塞流水线。")

    result = {"checker": "check_reflection", "scanned": scanned,
              "level": level, "count": len(FINDINGS), "findings": FINDINGS}
    if args.report:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
        print(f"报告已写入: {args.report}")
    sys.exit(1 if FINDINGS else 0)


if __name__ == "__main__":
    main()
