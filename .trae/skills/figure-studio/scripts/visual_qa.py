#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visual_qa.py — 图表渲染结果程序化视觉自检（零 token，确定性问题机器抓）

借鉴 scipilot-figure-skill 的视觉自检闭环思想，两种用法：

  模式 A（图内模式，出图时在代码里调用）：
      from visual_qa import audit_figure
      problems = audit_figure(fig)   # matplotlib Figure 对象 → 问题清单
  检查：文本越界裁切 / 刻度标签重叠 / CJK 缺字形（方框）。

  模式 B（文件扫描模式，机查/兜底用）：
      python visual_qa.py scan <figures目录或PNG文件>
  检查：空图/近空图、文件过小（疑似渲染残缺）、PNG dpi 元数据 <200。
  输出：控制台逐条 + 退出码（0=无 ERROR 级问题，1=有）。WARN 级只报告不阻塞。

级别：ERROR = 图不能交付（空图/缺字形/严重裁切）；WARN = 需人工看图裁定。
"""
import json
import sys
from pathlib import Path

import numpy as np


# ============================================================
# 模式 A：matplotlib Figure 对象检查
# ============================================================

def _check_cjk_glyphs(fig):
    """检查图内文本的字体是否含 CJK 字形（缺字形渲染为方框，ERROR）。"""
    from matplotlib import font_manager as fm
    problems = []
    # CJK 字体候选全集一处定义（visualization_style.CJK_FONT_SET），优先共享 import；
    # 机查独立运行（scan 模式）时 code_templates 不在 sys.path，回退到一致本地副本。
    try:
        from visualization_style import CJK_FONT_SET as cjk_fonts
    except Exception:
        cjk_fonts = {'SimSun', 'Noto Serif CJK SC', 'FangSong', 'KaiTi',
                     'Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei',
                     'Arial Unicode MS'}
    available = {f.name for f in fm.fontManager.ttflist}
    if not (cjk_fonts & available):
        # 全局无 CJK 字体：图内任何中文都是方框
        texts = [t for t in fig.findobj(match=lambda x: hasattr(x, 'get_text'))
                 if callable(getattr(t, 'get_text', None)) and any('一' <= c <= '鿿' for c in t.get_text())]
        if texts:
            problems.append(("ERROR", "缺字形",
                             f"系统无 CJK 字体但图内含 {len(texts)} 处中文文本——全部渲染为方框，须先装中文字体"))
    return problems


def _iter_texts_with_bbox(fig):
    """产出 (文本对象, 显示坐标 bbox)。渲染前需要先有 renderer。"""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for t in fig.findobj(match=lambda x: hasattr(x, 'get_window_extent')):
        if not callable(getattr(t, 'get_text', None)):
            continue
        s = t.get_text()
        if not s or not s.strip():
            continue
        try:
            bb = t.get_window_extent(renderer=renderer)
        except Exception:
            continue
        yield t, s, bb


def _check_text_clipping(fig):
    """文本超出图幅/坐标区 → 裁切（ERROR 级：交付后缺字）。"""
    problems = []
    W, H = fig.canvas.get_width_height()
    for t, s, bb in _iter_texts_with_bbox(fig):
        if bb.x1 < -2 or bb.y1 < -2 or bb.x0 > W + 2 or bb.y0 > H + 2:
            problems.append(("ERROR", "文本裁切",
                             f"文本 '{s[:14]}' 完全越出图幅（bbox=({bb.x0:.0f},{bb.y0:.0f},{bb.x1:.0f},{bb.y1:.0f})，图幅 {W}x{H}）"))
        elif bb.x0 < -2 or bb.y0 < -2 or bb.x1 > W + 2 or bb.y1 > H + 2:
            problems.append(("WARN", "文本裁切",
                             f"文本 '{s[:14]}' 部分越出图幅——可能被裁边，请人工看图裁定"))
    return problems


def _check_tick_overlap(fig):
    """刻度标签互相重叠（WARN：阅读困难）。"""
    problems = []
    for ax in fig.axes:
        for labels, axis_name in ((ax.get_xticklabels(), 'x'), (ax.get_yticklabels(), 'y')):
            boxes = []
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            for lb in labels:
                if not lb.get_text():
                    continue
                try:
                    boxes.append((lb.get_text(), lb.get_window_extent(renderer=renderer)))
                except Exception:
                    pass
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    a, b = boxes[i][1], boxes[j][1]
                    if a.overlaps(b):
                        # 重叠面积 >15% 才报（轻微相碰常见且可读）
                        ix = max(0, min(a.x1, b.x1) - max(a.x0, b.x0))
                        iy = max(0, min(a.y1, b.y1) - max(a.y0, b.y0))
                        inter = ix * iy
                        small = min(a.width * a.height, b.width * b.height)
                        if small > 0 and inter / small > 0.15:
                            problems.append(("WARN", "刻度重叠",
                                             f"{axis_name} 轴刻度 '{boxes[i][0]}' 与 '{boxes[j][0]}' 重叠 "
                                             f"{inter / small:.0%}——旋转标签或减稀刻度"))
                            return problems  # 每轴报一次足够
    return problems


def audit_figure(fig):
    """对 matplotlib Figure 做程序自检，返回 [(级别, 规则, 说明)]。打印并返回。"""
    problems = []
    problems += _check_cjk_glyphs(fig)
    try:
        problems += _check_text_clipping(fig)
        problems += _check_tick_overlap(fig)
    except Exception as e:  # 渲染后端异常不阻塞出图
        problems.append(("WARN", "自检异常", f"渲染态检查未完成：{e}"))
    for lv, rule, msg in problems:
        print(f"[visual_qa] {lv} [{rule}] {msg}")
    if not problems:
        print("[visual_qa] PASS 程序自检无异常")
    return problems


# ============================================================
# 模式 B：PNG 文件扫描（机查/兜底）
# ============================================================

def check_png(path):
    """单张 PNG 文件检查，返回 [(级别, 规则, 说明)]。"""
    from PIL import Image
    problems = []
    p = Path(path)
    if p.stat().st_size < 5 * 1024:
        problems.append(("WARN", "文件过小", f"{p.name} 仅 {p.stat().st_size} 字节——疑似渲染残缺，请人工看图"))
        return problems
    try:
        img = Image.open(p).convert("L")
        arr = np.asarray(img, dtype=float)
        if arr.std() < 2.0:
            problems.append(("ERROR", "空图", f"{p.name} 像素方差 {arr.std():.2f}≈0——疑似空白图"))
        dpi = Image.open(p).info.get("dpi")
        if dpi and dpi[0] < 200:
            problems.append(("WARN", "dpi 偏低", f"{p.name} dpi={dpi[0]:.0f} <200——论文要求 PNG 300dpi"))
    except Exception as e:
        problems.append(("WARN", "读取失败", f"{p.name} 无法解析：{e}"))
    return problems


def scan(target):
    """扫描目录下全部 PNG（或单文件），打印并返回问题汇总。"""
    p = Path(target)
    files = [p] if p.is_file() else sorted(p.rglob("*.png"))
    all_problems = {}
    for f in files:
        probs = check_png(f)
        if probs:
            all_problems[str(f)] = probs
            for lv, rule, msg in probs:
                print(f"{lv} [{rule}] {msg}")
    if not all_problems:
        print(f"PASS 扫描 {len(files)} 张 PNG 无异常")
    return all_problems


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "scan":
        problems = scan(sys.argv[2])
        has_err = any(lv == "ERROR" for ps in problems.values() for lv, _, _ in ps)
        print(json.dumps({"files_with_problems": len(problems), "has_error": has_err}))
        sys.exit(1 if has_err else 0)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
