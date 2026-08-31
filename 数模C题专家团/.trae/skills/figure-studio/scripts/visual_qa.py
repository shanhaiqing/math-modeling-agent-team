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
from matplotlib import text as mtext


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
        texts = [t for t in fig.findobj(match=lambda x: isinstance(x, mtext.Text))
                 if any('一' <= c <= '鿿' for c in t.get_text())]
        if texts:
            problems.append(("ERROR", "缺字形",
                             f"系统无 CJK 字体但图内含 {len(texts)} 处中文文本——全部渲染为方框，须先装中文字体"))
    return problems


def _iter_texts_with_bbox(fig):
    """产出 (文本对象, 显示坐标 bbox)。渲染前需要先有 renderer。"""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for t in fig.findobj(match=lambda x: isinstance(x, mtext.Text)):
        ax_ = getattr(t, 'axes', None)
        if ax_ is not None and getattr(ax_, 'zaxis', None) is not None:
            continue  # mplot3d 轴上文本的 window extent 不可靠（误报裁切），跳过
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
    if any(getattr(a, 'zaxis', None) is not None for a in fig.axes):
        return problems  # mplot3d 全局文本 bbox 不可靠（漂移量不定），裁切检查仅覆盖 2D 图
    W, H = fig.canvas.get_width_height()
    for t, s, bb in _iter_texts_with_bbox(fig):
        # 数据坐标系/特殊变换下 bbox 可能异常巨大：超图幅 8 倍视为变换不可靠跳过（防误报）
        if bb.x0 < -8 * W or bb.x1 > 8 * W or bb.y0 < -8 * H or bb.y1 > 8 * H:
            continue
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
        if getattr(ax, 'zaxis', None) is not None:
            continue  # mplot3d 刻度 bbox 不可靠，跳过
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


def _check_grayscale_legibility(fig):
    """灰度分离度启发（WARN）：离散分类图的主题色两两灰度差不足 → 色盲/灰阶打印难区分。
    免检情形：主题色 <2（无多色对比需求）或 >8（疑似连续色板，如热力/3D 响应面）。"""
    from matplotlib.colors import to_rgba
    problems = []
    counter = {}
    for obj in fig.findobj():
        for attr in ("get_facecolor", "get_edgecolor"):
            getter = getattr(obj, attr, None)
            if not callable(getter):
                continue
            try:
                c = to_rgba(getter())
            except Exception:
                continue
            if len(c) == 4 and c[3] > 0.5:
                key = (round(c[0], 2), round(c[1], 2), round(c[2], 2))
                counter[key] = counter.get(key, 0) + 1
    themed = [k for k, _ in sorted(counter.items(), key=lambda kv: -kv[1])[:10]
              if 0.15 < sum(k) < 2.6]   # 排除近白背景/近黑文字
    if len(themed) < 2 or len(themed) > 8:
        return problems
    grays = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in themed]
    for i in range(len(grays)):
        for j in range(i + 1, len(grays)):
            if abs(grays[i] - grays[j]) < 0.15:
                problems.append(("WARN", "灰阶难区分",
                                 f"主题色 {themed[i]} 与 {themed[j]} 灰度差 {abs(grays[i] - grays[j]):.2f} < 0.15，"
                                 "色盲/灰阶打印下难区分——换 OKABE_ITO 色板或加标记/图案"))
                return problems
    return problems


def audit_figure(fig):
    """对 matplotlib Figure 做程序自检，返回 [(级别, 规则, 说明)]。打印并返回。"""
    problems = []
    problems += _check_cjk_glyphs(fig)
    try:
        problems += _check_grayscale_legibility(fig)
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
