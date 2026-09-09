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


def check_marks(text, fname):
    """R2/R3/R4：解析逐项标注与依据质量。"""
    # 表格形式（s4 模板）：| ... | ✓/⚠️/✗ | 依据 |
    # 散文形式（s1-s3）：1.xxx ✓ 依据
    rows = re.findall(r"^\|.*\|\s*(✓|⚠️|✗|✅|❌)\s*\|(.*?)\|\s*$", text, re.M)
    marks = [(m.group(1), text[m.end():m.end() + 40]) for m in re.finditer(r"(✓|⚠️|✗)", text)]

    n_ok = sum(1 for m, _ in marks if m in ("✓", "✅"))
    n_bad = sum(1 for m, _ in marks if m in ("⚠️", "✗", "❌"))

    if n_ok >= 5 and n_bad == 0:
        warn(fname, f"R2 全 ✓ 无警示：{n_ok} 个 ✓、0 个 ⚠️/✗——层 1 逐项扫描应有区分度，"
                    f"全部通过疑为未真实展开（AGENTS.md 红队机制禁止无差别 ✓）")

    empty = short = 0
    for mark, tail in marks:
        cleaned = re.sub(r"[\s|：:，,。\-—*#`]", "", tail)
        if not cleaned:
            empty += 1
        elif len(cleaned) < 20 and not EVIDENCE_HINT.search(tail):
            short += 1
    if rows:  # 表格形式另查说明列
        for _mark, note in rows:
            cleaned = re.sub(r"[\s|：:，,。\-—*#`\[\]]", "", note)
            if not cleaned or cleaned in ("具体依据", "依据"):
                empty += 1
            elif len(cleaned) < 20 and not EVIDENCE_HINT.search(note):
                short += 1
    if empty:
        warn(fname, f"R3 空依据 {empty} 处：标记后无任何内容——每个 ✓ 须附证据指针（文件+行号/机查报告条目）")
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
