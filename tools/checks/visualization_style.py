#!/usr/bin/env python3
"""
可视化样式模板
建模与写作阶段统一使用。确保图表符合论文规范（300dpi、PDF+PNG 双格式）。
缺省 `cumcm`：中文衬线优先 SimSun。`contest_profile=shuwei_en`：西文衬线（Times New Roman），
不强制 CJK；无中文字体不警告。读项目根 `pipeline_state.json` 或 `setup_style(contest_profile=)`。

=== 视觉体系三原则（出图前对照 .trae/papers/图表类型参考库.md 第五节） ===
  1. 低饱和学术配色：禁止 matplotlib 默认 tab10 高饱和色，统一用本模板 PALETTE；
     柱形图填充统一半透明 alpha≈0.5（类 fill_betweenx 波带风格），避免大色块压抑。
  2. 高信息密度：相关量尽量组合为 (a)/(b) 多面板（new_figure），单图单信息视为浪费。
  3. 图内统计标注：关键结论用 annotate_badge / annotate_callout 直接标在图上，
     方法说明（口径/置信水平等）留给论文 caption，不写进图标题。

=== 库选择规则（强制） ===

┌─────────────────────────────────────────────────────────────┐
│ 优先用 seaborn 的场景：                                      │
│   • 热力图 (heatmap)         → sns.heatmap()                │
│   • 箱线图 (boxplot)         → sns.boxplot()                │
│   • 小提琴图 (violin)        → sns.violinplot()             │
│   • 分布图 (dist/hist/kde)   → sns.histplot() / sns.kdeplot()│
│   • 散点矩阵 (pairplot)      → sns.pairplot()               │
│   • 多变量分组对比           → sns.catplot() / sns.relplot()│
│                                                             │
│ 用 matplotlib 的场景（本模板不再提供 plot_bar/plot_tornado/     │
│   plot_line/plot_scatter/plot_heatmap 等成品封装——它们签名过窄、  │
│   无法承载题内自定义装饰，agent 实际从不调用；此类图一律自绘）：  │
│   • 折线/柱状/散点/Tornado/热力等需自定义装饰的图                │
│     → 自绘（new_figure + annotate_* 积木 + COLORS/BAR_ALPHA）   │
│   • 区间/误差表达 → plot_confint() / plot_errorbar()（保留封装） │
│   • 需要自定义标注/子图/复杂布局                                 │
│   • seaborn 不支持的特殊图表                                     │
└─────────────────────────────────────────────────────────────┘

原则：seaborn 能画的统计图优先用 seaborn（默认美观度更高，代码更短）；
      自定义/特殊图表用 matplotlib 自绘（灵活度更高）。
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 无头环境兜底（Bash 执行/比赛环境无显示，防止 TkAgg 崩溃）
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import numpy as np
import seaborn as sns

LEGAL_PROFILES = ("cumcm", "shuwei_zh", "shuwei_en")
ACTIVE_CONTEST_PROFILE = "cumcm"

# ============================================================
# 全局样式设置
# ============================================================

# 自动检测可用的中文字体（衬线优先：宋体与论文正文同族，视觉统一）
# 修订建议 #10：SimSun/宋体是衬线，与 sans-serif 语义不符，按衬线/无衬线分族回落
_SERIF_CJK_CANDIDATES = ['SimSun', 'Noto Serif CJK SC', 'FangSong', 'KaiTi',
                         'Arial Unicode MS']
_SANS_CJK_CANDIDATES = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei']
# CJK 字体候选全集（一处定义，供 visual_qa.py 等复用，避免多处硬编码不一致）
CJK_FONT_SET = set(_SERIF_CJK_CANDIDATES) | set(_SANS_CJK_CANDIDATES)
_available_fonts = {f.name for f in fm.fontManager.ttflist}
_cjk_font = None
_cjk_family = 'sans-serif'
for _font in _SERIF_CJK_CANDIDATES:
    if _font in _available_fonts:
        _cjk_font = _font
        _cjk_family = 'serif'
        break
if _cjk_font is None:
    for _font in _SANS_CJK_CANDIDATES:
        if _font in _available_fonts:
            _cjk_font = _font
            break

_WESTERN_SERIF_CANDIDATES = [
    "Times New Roman", "Times", "Liberation Serif", "Nimbus Roman No9 L", "DejaVu Serif",
]


def resolve_contest_profile(cli_value=None, search_roots=None):
    """--contest-profile / 显式参数优先；否则读 pipeline_state.json；非法/缺失 → cumcm。"""
    if cli_value:
        v = str(cli_value).strip().lower()
        return v if v in LEGAL_PROFILES else "cumcm"
    roots = []
    for r in search_roots or []:
        roots.append(Path(r))
    cwd = Path.cwd()
    roots.extend([cwd, *list(cwd.parents)[:6]])
    seen = set()
    for r in roots:
        p = r if r.name == "pipeline_state.json" else r / "pipeline_state.json"
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        v = str(data.get("contest_profile") or "").strip().lower()
        return v if v in LEGAL_PROFILES else "cumcm"
    return "cumcm"


def _first_available_font(candidates):
    for name in candidates:
        if name in _available_fonts:
            return name
    return None


def _western_serif_font():
    return _first_available_font(_WESTERN_SERIF_CANDIDATES) or "DejaVu Serif"


def _cjk_font_rc():
    return {
        "font.family": [_cjk_family],
        "font.serif": [_cjk_font, "DejaVu Serif"] if _cjk_font else ["DejaVu Serif"],
        "font.sans-serif": [_cjk_font, "DejaVu Sans"] if _cjk_font else ["DejaVu Sans"],
        "mathtext.fontset": "dejavusans",
    }


def _western_font_rc():
    west = _western_serif_font()
    return {
        "font.family": ["serif"],
        "font.serif": [west, "DejaVu Serif"],
        "font.sans-serif": ["DejaVu Sans"],
        "mathtext.fontset": "stix",
    }


if _cjk_font:
    plt.rcParams['font.family'] = [_cjk_family]
    plt.rcParams['font.serif'] = [_cjk_font, 'DejaVu Serif']
    plt.rcParams['font.sans-serif'] = [_cjk_font, 'DejaVu Sans']
    print(f"[可视化] 检测到中文字体: {_cjk_font}（{_cjk_family} 族）")
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    print("[可视化] [警告] 未检测到中文字体，图表中文可能显示为方框")

plt.rcParams['axes.unicode_minus'] = False
# 修订建议 #10：数学字体固定 DejaVu 系，避免负号/数学符号缺字形渲染为方框
plt.rcParams['mathtext.fontset'] = 'dejavusans'
# 修订建议 #11：PDF/PS 真字体嵌入（Type 42），避免期刊系统因 Type 3 位图报错
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

# 图幅统一锚点（2026-08 批次，一处定义：出图层与论文排版层 1:1 对应）
# 论文端：\includegraphics[width=0.9\textwidth]（《LaTeX格式规范》§四）
# 出图端：canvas 总宽锁定 CU_TEXTWIDTH_IN（A4 单栏 0.9\textwidth ≈ 14.6cm ≈ 5.75in）。
# matplotlib 字号是图形绝对单位：canvas 宽与最终展示宽 1:1 时字号不失真；
# 两者不一致时缩放即失真——禁止导出后再用 includegraphics 缩放补救。
CU_TEXTWIDTH_IN = 5.75                     # A4 单栏展示宽（0.9\textwidth ≈ 14.6cm）
SINGLE_COLUMN = (CU_TEXTWIDTH_IN, 3.6)     # 单面板占满栏宽（宽高比 8:5）
# 多面板图幅一律由 new_figure 按面板数自动计算（总宽恒为 CU_TEXTWIDTH_IN），不另设常量

# 颜色方案（低饱和学术色板，Okabe-Ito 降饱和变体；禁用 tab10 默认高饱和）
COLORS = {
    "primary": "#4C78A8",
    "secondary": "#E8927C",
    "tertiary": "#7FB89B",
    "quaternary": "#D6604D",
    "palette": ["#4C78A8", "#E8927C", "#7FB89B", "#B48EAD",
                "#D4A94E", "#8C6D5C", "#6FA8DC", "#9AA0A6"]
}

# 色盲安全 8 色标准集（调研入库 2026-08）：Okabe-Ito/Wong 全色觉障碍可区分标准色。
# 离散分类需要"任意色觉障碍下均可区分"（尤其灰阶打印场景）时优先用本集；
# COLORS['palette'] 为降饱和学术变体，两者并存不冲突。
OKABE_ITO = ['#E69F00', '#56B4E9', '#009E73', '#F0E442',
             '#0072B2', '#D55E00', '#CC79A7', '#000000']

# 线型
LINE_STYLES = ['-', '--', '-.', ':']

# 标记
MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p']

# 柱形图填充半透明（批次 B10：统一 alpha≈0.5，fig8 波峰 fill_betweenx 风格，避免大色块压抑）
BAR_ALPHA = 0.5


def _apply_grid(ax, axis='both'):
    """淡网格：细实线低透明度，仅作读数辅助，不抢视觉主体。"""
    ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.5, axis=axis)


# ============================================================
# CMasher 科学色板（P1-a：无障碍/期刊级配色）
# ============================================================

# 是否成功加载 CMasher（供调用方判断）
CMASHER_ACTIVE = False
try:
    import cmasher  # noqa: F401（注册 cmr.* 科学 colormap）
    CMASHER_ACTIVE = True
except Exception as _e:
    _CMASHER_IMPORT_ERR = _e
    cmasher = None

# 科学 colormap 选择（未安装 CMasher 时优雅回退到 matplotlib 内置同等色板）。
# 仅做"选择"，不承担任何计算——数值正确性由输入数据保证。
COLORMAPS = {
    "sequential": "cmr.sunburst" if CMASHER_ACTIVE else "viridis",  # 顺序：热力图/密度/单调量
    "diverging": "cmr.fusion" if CMASHER_ACTIVE else "RdBu_r",    # 发散：正负/盈亏临界对比
    "cyclic": "cmr.seasons" if CMASHER_ACTIVE else "twilight",     # 循环：角度/相位
    # 修订建议 #1：分类离散色禁止 colormap（防止回退 tab10 高饱和），
    # 一律走 COLORS['palette']（离散色板）。None 作哨兵：误用作 colormap 会显式报错而非静默 tab10。
    "qualitative": None,
}


# 是否成功应用 SciencePlots 期刊风格（供调用方判断）
SCIENCE_STYLE_ACTIVE = False


def _shared_style_rc(en):
    """SciencePlots / 降级共用的网格、字号、字体嵌入。字体栈按剖面覆盖。"""
    rc = {
        "axes.unicode_minus": False,
        "axes.formatter.use_mathtext": False,
        "grid.alpha": 0.15,
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "figure.dpi": 100,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
    rc.update(_western_font_rc() if en else _cjk_font_rc())
    return rc


def setup_style(contest_profile=None):
    """
    设置全局 matplotlib + seaborn 样式。

    优先应用 SciencePlots 的 'science' 期刊风格（提升视觉期刊度）；
    若未安装 scienceplots 或风格加载失败，优雅降级到内置 rcParams 直设。
    降级策略确保无该依赖时团队仍可正常出图。

    contest_profile 缺省时读 pipeline_state.json（非法/缺失 → cumcm）。
    shuwei_en：Times 系衬线，不把 CJK 放进回退栈，无中文字体不警告。
    """
    global SCIENCE_STYLE_ACTIVE, ACTIVE_CONTEST_PROFILE
    profile = resolve_contest_profile(contest_profile)
    ACTIVE_CONTEST_PROFILE = profile
    en = profile == "shuwei_en"
    applied_science = False

    # --- 尝试 SciencePlots 期刊风格（P0：视觉呈现升级） ---
    try:
        import scienceplots  # noqa: F401（注册 science 风格）
        # 优先用带网格的 'science' 变体；CJK 或英文赛附 'no-latex' 避免依赖 LaTeX
        style_list = ["science", "grid"]
        if en or _cjk_font:
            style_list.append("no-latex")
        plt.style.use(style_list)
        applied_science = True
    except Exception as e:
        print(f"[可视化] SciencePlots 未生效，使用内置样式回退: {e}")

    if applied_science:
        SCIENCE_STYLE_ACTIVE = True
        print("[可视化] 已应用 SciencePlots 'science' 期刊风格")
        mpl.rcParams.update(_shared_style_rc(en))
        if en:
            print(f"[可视化] shuwei_en 西文衬线: {_western_serif_font()}（无 CJK 回退）")
        return

    # --- 降级分支：内置 rcParams 直设 ---
    sns.set_style("whitegrid")  # seaborn 全局样式
    fallback = {
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "lines.linewidth": 1.5,
    }
    fallback.update(_shared_style_rc(en))
    mpl.rcParams.update(fallback)
    if en:
        print(f"[可视化] shuwei_en 西文衬线: {_western_serif_font()}（无 CJK 回退）")


def save_figure(fig, filename: str, formats: list = None):
    """
    保存图表为 PDF + PNG 双格式。
    
    修订建议 #11：PDF/SVG/EPS 是矢量，不传 dpi 保留矢量精度；
    PNG/JPG/TIFF 用 300 dpi，并显式指定白底色（透明不可用于期刊投稿）。
    
    Args:
        fig: matplotlib figure 对象
        filename: 不含扩展名的文件名
        formats: 保存格式列表，默认 ['pdf', 'png']
    """
    if formats is None:
        formats = ['pdf', 'png']
    
    # 矢量格式列表（不传 dpi）
    _VECTOR = {'.pdf', '.svg', '.eps', '.ps'}
    # 位图格式列表（传 300 dpi）
    _RASTER = {'.png', '.jpg', '.jpeg', '.tiff', '.tif'}
    
    for fmt in formats:
        path = f"{filename}.{fmt}"
        ext = f".{fmt.lower()}"
        save_kw = {'bbox_inches': 'tight'}
        if ext in _RASTER:
            save_kw['dpi'] = 300
            save_kw['facecolor'] = 'white'
            save_kw['edgecolor'] = 'white'
            save_kw['transparent'] = False
        # 矢量格式不传 dpi（保留矢量精度）
        fig.savefig(path, **save_kw)
        print(f"[完成] 图表已保存: {path}")


def new_figure(n_panels=2, figsize=None, layout=None, sharex=False, sharey=False):
    """
    创建 (a)/(b) 多面板图，返回 (fig, axes 列表)。

    图幅纪律（一处定义，详则见《图表类型参考库》§五.6）：
    canvas 总宽恒为 CU_TEXTWIDTH_IN（=论文 0.9\\textwidth≈14.6cm），与
    includegraphics 1:1 对应，保证字号不失真；面板越多每面板展示宽越小——
    图内最小字号按"每面板展示宽=栏宽÷横排面板数"折算后须仍 ≥ 正文字号 70%
    （正文 12pt → 图内最小字 ≥9pt）。
    布局默认：2 面板横排 (1,2)；3 面板横排 (1,3)（每面板≈4.9cm，内容须精简）；
    ≥4 面板 2×2 网格，禁止单行横排 >3 面板（可读性崩塌）。

    Args:
        n_panels: 面板总数
        layout: (nrows, ncols) 网格，None 时按上述默认规则
        figsize: 整图尺寸；None 时自动（总宽=CU_TEXTWIDTH_IN，行高按面板宽高比 4:3）
        sharex/sharey: 是否共享坐标轴
    """
    if layout is None:
        if n_panels <= 1:
            layout = (1, 1)
        elif n_panels == 2:
            layout = (1, 2)
        elif n_panels == 3:
            layout = (1, 3)
        else:
            ncols = 2
            nrows = (n_panels + 1) // 2
            layout = (nrows, ncols)
    nrows, ncols = layout
    if figsize is None:
        panel_w = CU_TEXTWIDTH_IN / ncols
        panel_h = panel_w / 1.35          # 单面板宽高比 ≈4:3
        figsize = (CU_TEXTWIDTH_IN, panel_h * nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize,
                             sharex=sharex, sharey=sharey)
    axes = np.array(axes, dtype=object).ravel().tolist()
    for i, ax in enumerate(axes):
        if i >= n_panels:
            ax.set_axis_off()             # layout 网格多于面板数时关闭多余格
            continue
        # SimSun 无 bold 字形，用字号区分层级而非字重
        ax.text(-0.12, 1.06, f"({chr(97 + i)})", transform=ax.transAxes,
                fontsize=11, va='top')
    return fig, axes


def annotate_badge(ax, text, xy, color=None, fontsize=8):
    """
    图内统计徽章：在数据坐标 xy 处放置带边框的结论性标注
    （如"中位 59%""导通"），白底彩框，示例论文常见手法。
    """
    color = color or COLORS["primary"]
    ax.annotate(text, xy=xy, fontsize=fontsize, color=color,
                bbox=dict(boxstyle="round,pad=0.3", fc="white",
                          ec=color, alpha=0.9))


def annotate_callout(ax, text, xy, xytext, color=None, fontsize=8):
    """
    图内引导注释：箭头从 xytext 指向数据点 xy
    （如最优解星标说明、临界点解释），适合对单个关键点的解释。
    """
    color = color or COLORS["quaternary"]
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=fontsize, color=color,
                arrowprops=dict(arrowstyle="->", color=color, lw=1.0),
                bbox=dict(boxstyle="round,pad=0.3", fc="white",
                          ec=color, alpha=0.9))


# ============================================================
# Seaborn 专用封装函数
# ============================================================

def plot_boxplot(data, x=None, y=None, hue=None, xlabel="", ylabel="",
                 filename="figures/boxplot"):
    """
    绘制箱线图（seaborn）。

    Args:
        data: DataFrame 或 数组列表
        x: x 轴分组变量（DataFrame 列名）
        y: y 轴数值变量（DataFrame 列名）
        hue: 颜色分组变量
    """
    setup_style()
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)

    if isinstance(data, list):
        # 多组数据对比
        sns.boxplot(data=data, ax=ax, palette=COLORS["palette"])
    else:
        sns.boxplot(data=data, x=x, y=y, hue=hue, ax=ax, palette=COLORS["palette"])

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_violin(data, x=None, y=None, hue=None, xlabel="", ylabel="",
                filename="figures/violin"):
    """
    绘制小提琴图（seaborn）。适合展示分布形状 + 多组对比。
    """
    setup_style()
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)

    sns.violinplot(data=data, x=x, y=y, hue=hue, ax=ax,
                   palette=COLORS["palette"], inner="quartile")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_distribution(data, x=None, kde=True, bins="auto", xlabel="",
                      filename="figures/distribution"):
    """
    绘制分布直方图 + KDE 曲线（seaborn）。

    Args:
        data: 数据数组或 DataFrame
        x: DataFrame 列名
        kde: 是否叠加核密度估计曲线
    """
    setup_style()
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)

    sns.histplot(data=data, x=x, kde=kde, bins=bins, ax=ax, color=COLORS["primary"])

    ax.set_xlabel(xlabel)
    ylabel_default = "Frequency" if ACTIVE_CONTEST_PROFILE == "shuwei_en" else "频数"
    ax.set_ylabel(ylabel_default)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


# ============================================================
# 纯可视化封装（只画，不算）
# ============================================================
# 以下函数只负责把"已由建模/求解层算好的数值"画对、画统一。
# 它们不承担任何统计计算（置信区间怎么算、蒙特卡洛怎么抽样、灵敏度怎么扰动
# 都是问题依赖的，必须由求解脚本按题目语义完成）。正确性由：
#   ① 输入数值（来自已验证的求解结果）  ② 函数内输入校验  ③ 单元测试 共同保证。

def plot_confint(x, y_mean, y_lower, y_upper, xlabel="", ylabel="",
                 filename="figures/confint", color=None, fill_alpha=0.25):
    """
    绘制"点估计 + 置信区间波带"（纯可视化，不计算置信区间）。

    直接消费已算好的均值与上下界，用半透明波带 + 中位线 + 端点的期刊风格呈现。
    适用于：置信区间、蒙特卡洛绕动带、灵敏度区间等一切"点+区间"表达。

    Args:
        x: x 轴数据（1D array-like）
        y_mean: 各点中心值（1D）
        y_lower: 各点下界（1D，须满足 y_lower[i] <= y_mean[i]）
        y_upper: 各点上界（1D，须满足 y_mean[i] <= y_upper[i]）
        color: 主色；None 时用 COLORS["primary"]
        fill_alpha: 波带透明度（0~1）
    """
    import numpy as _np
    setup_style()
    x = _np.asarray(x, dtype=float)
    y_mean = _np.asarray(y_mean, dtype=float)
    y_lower = _np.asarray(y_lower, dtype=float)
    y_upper = _np.asarray(y_upper, dtype=float)

    # 输入校验：长度一致 + 上下界与均值自洽（纯可视化层不推断，只拦截明显传错）
    if not (len(x) == len(y_mean) == len(y_lower) == len(y_upper)):
        raise ValueError("plot_confint: x/y_mean/y_lower/y_upper 长度必须一致")
    if _np.any(y_lower > y_mean) or _np.any(y_mean > y_upper):
        raise ValueError("plot_confint: 须满足 y_lower<=y_mean<=y_upper（区间不成立）")

    color = color or COLORS["primary"]
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    ax.fill_between(x, y_lower, y_upper, color=color, alpha=fill_alpha, linewidth=0)
    ax.plot(x, y_mean, color=color, linewidth=1.8, label="point estimate")
    ax.plot(x, y_lower, color=color, linestyle="--", linewidth=1.0, alpha=0.7)
    ax.plot(x, y_upper, color=color, linestyle="--", linewidth=1.0, alpha=0.7)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_grid(ax)
    ax.legend()
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_errorbar(x, y, yerr=None, xerr=None, capsize=4, xlabel="", ylabel="",
                  filename="figures/errorbar", color=None):
    """
    绘制带误差棒的散点/折线图（纯可视化，不计算误差）。

    Args:
        x: x 轴数据
        y: 中心值
        yerr: y 方向误差，可为标量（对称）或 (2, N) 数组（非对称下/上界）
        xerr: x 方向误差（可选）
        capsize: 误差棒端帽大小
    """
    import numpy as _np
    setup_style()
    x = _np.asarray(x, dtype=float)
    y = _np.asarray(y, dtype=float)
    color = color or COLORS["primary"]

    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    ax.errorbar(x, y, yerr=yerr, xerr=xerr, fmt="o-", capsize=capsize,
                color=color, markersize=5, linewidth=1.5)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_grid(ax)
    save_figure(fig, filename)
    plt.close(fig)
    return fig