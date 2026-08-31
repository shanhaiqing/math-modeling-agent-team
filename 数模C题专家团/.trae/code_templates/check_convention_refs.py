#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_convention_refs.py — 惯例编号引用完整性 + 条款锚点目录对账机查

[契约] 惯例编号引用完整性 + 条款锚点目录对账（C 版，移植自 B 系统；锚点目录缺失降级 WARN）：
  1. 扫描全系统「惯例 X.Y」编号引用，与惯例正文实际条目比对，悬空 → ERROR
     （防编号漂移后引用失联：惯例七节规定新条目仅节末追加）
  2. 文首「条款锚点目录」声明的条目编号与正文实际编号逐节对账，
     不一致 → ERROR（目录必须与正文同步维护）

用法：python check_convention_refs.py [项目根]
退出码：0 = 通过；1 = 存在 ERROR；2 = 用法错误
"""
import json
import re
import sys
from pathlib import Path

CONV = Path(__file__).resolve().parent.parent / "papers" / "国赛公开惯例.md"
SEC_RE = re.compile(r"^##\s+([一二三四五六七])、")
ITEM_RE = re.compile(r"^(\d+)\.\s")
TOC_SEC_RE = re.compile(r"^- \*\*([一二三四五六七])、")
REF_RE = re.compile(r"惯例\s*([一二三四五六七])\.(\d+)")

N2I = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}
EXCLUDE_DIRS = {".git", "_quarantine", "_isolated_refs", ".venv", "venv",
                "node_modules", "__pycache__"}

FINDINGS = []


def error(rule, loc, msg):
    FINDINGS.append({"level": "ERROR", "rule": rule, "location": loc, "message": msg})


def ok(rule, msg):
    FINDINGS.append({"level": "PASS", "rule": rule, "location": "", "message": msg})


def parse_body(text):
    """解析惯例正文：{节汉字: set(条目号)}（七节无编号条目时为空集）。"""
    secs, cur = {}, None
    for line in text.splitlines():
        m = SEC_RE.match(line)
        if m:
            cur = m.group(1)
            secs.setdefault(cur, set())
            continue
        m = ITEM_RE.match(line)
        if m and cur:
            secs[cur].add(int(m.group(1)))
    return secs


def parse_toc(text):
    """解析文首「条款锚点目录」节：{节汉字: set(条目号)}。"""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("## 条款锚点目录")), None)
    if start is None:
        return None
    toc = {}
    for l in lines[start + 1:]:
        if l.startswith("## "):
            break
        m = TOC_SEC_RE.match(l)
        if not m:
            continue
        sec = m.group(1)
        body = l[m.end():]
        body = body.split("**", 1)[1] if "**" in body else body
        body = body.lstrip("：:\u3000 ")   # 剥掉「一、方法学惯例**」与首编号之间的"："分隔符
        nums = set()
        for seg in re.split(r"[｜|]", body):
            mm = re.match(r"\s*(\d+)\s", seg)
            if mm:
                nums.add(int(mm.group(1)))
        toc[sec] = nums
    return toc


def scan_refs(root):
    """扫描全系统 md/py 的「惯例 X.Y」引用 → 悬空清单。"""
    refs = {}
    for f in root.rglob("*"):
        if not f.is_file() or f.suffix not in (".md", ".py", ".json"):
            continue
        if any(p in EXCLUDE_DIRS for p in f.parts):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in REF_RE.finditer(text):
            refs.setdefault((m.group(1), int(m.group(2))), []).append(
                str(f.relative_to(root)))
    return refs


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent.parent
    if not CONV.is_file():
        print(f"用法错误：惯例文件不存在 {CONV}")
        sys.exit(2)
    text = CONV.read_text(encoding="utf-8")

    secs = parse_body(text)
    if not secs:
        print("用法错误：未解析到惯例正文条目")
        sys.exit(2)

    # 检查 1：引用完整性
    refs = scan_refs(root)
    n_err = 0
    for (sec, num), files in sorted(refs.items(), key=lambda x: (N2I[x[0][0]], x[0][1])):
        n = "惯例%d.%d" % (N2I[sec], num)
        if num not in secs.get(sec, set()):
            n_err += 1
            error("引用", n, f"悬空引用（正文无此条目），出现在 {len(files)} 个文件: {', '.join(files[:3])}")
    if n_err == 0 and refs:
        ok("引用", f"扫描 {len(refs)} 处惯例编号引用，零悬空")

    # 检查 2：目录对账（C 版适配：惯例未实施「条款锚点目录」时降级为 WARN，不阻塞）
    toc = parse_toc(text)
    if toc is None:
        print("WARN  [目录] 本版惯例未实施「条款锚点目录」（渐进式披露待落地），跳过目录对账")
    else:
        for sec, body_nums in sorted(secs.items(), key=lambda x: N2I[x[0]]):
            if not body_nums:
                continue  # 七节等无编号条目节，目录无声明即一致
            toc_nums = toc.get(sec)
            if toc_nums is None:
                error("目录", f"{sec}节", "目录未声明该节条目清单")
            elif toc_nums != body_nums:
                missing = sorted(body_nums - toc_nums)
                extra = sorted(toc_nums - body_nums)
                error("目录", f"{sec}节",
                      f"目录与正文不一致：目录缺 {missing or '无'}，目录多 {extra or '无'}")
            else:
                ok("目录", f"{sec}节：目录 {len(toc_nums)} 条与正文一致")

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    for f in FINDINGS:
        print(f"{f['level']:5s} [{f['rule']}] {f['location']} {f['message']}")
    print(f"汇总：{n_err} ERROR")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()