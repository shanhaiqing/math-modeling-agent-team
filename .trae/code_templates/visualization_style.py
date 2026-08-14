#!/usr/bin/env python3
"""
可视化样式模板
建模与写作阶段统一使用。确保图表符合论文规范（中文字体自动检测优先 Microsoft YaHei、300dpi、PDF+PNG 双格式）。

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
│ 用 matplotlib 的场景：                                       │
│   • 折线图 (line)   → plot_line()                           │
│   • 柱状图 (bar)    → plot_bar()                            │
│   • 散点图 (scatter)→ plot_scatter()                        │
│   • Tornado 图      → plot_tornado()                        │
│   • 需要自定义标注/子图/复杂布局                             │
│   • seaborn 不支持的特殊图表                                 │
└─────────────────────────────────────────────────────────────┘

原则：seaborn 能画的统计图优先用 seaborn（默认美观度更高，代码更短）；
      自定义/特殊图表用 matplotlib（灵活度更高）。
"""

import matplotlib
matplotlib.use("Agg")  # 无头环境兜底（Bash 执行/比赛环境无显示，防止 TkAgg 崩溃）
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import numpy as np
import seaborn as sns

# ============================================================
# 全局样式设置
# ============================================================

# 自动检测可用的中文字体
_CJK_FONT_CANDIDATES = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong',
                         'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Arial Unicode MS']
_available_fonts = {f.name for f in fm.fontManager.ttflist}
_cjk_font = None
for _font in _CJK_FONT_CANDIDATES:
    if _font in _available_fonts:
        _cjk_font = _font
        break

if _cjk_font:
    plt.rcParams['font.sans-serif'] = [_cjk_font, 'DejaVu Sans']
    print(f"[可视化] 检测到中文字体: {_cjk_font}")
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    print("[可视化] ⚠️ 未检测到中文字体，图表中文可能显示为方框")

plt.rcParams['axes.unicode_minus'] = False

# 图尺寸（单栏/双栏）
SINGLE_COLUMN = (6, 4)    # 单栏图
DOUBLE_COLUMN = (8, 5)    # 双栏大图
SQUARE = (5, 5)           # 正方形图

# 颜色方案
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "tertiary": "#2ca02c",
    "quaternary": "#d62728",
    "palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
                "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
}

# 线型
LINE_STYLES = ['-', '--', '-.', ':']

# 标记
MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p']


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
    "qualitative": "tab10",                                         # 定性：分类离散
}


# 是否成功应用 SciencePlots 期刊风格（供调用方判断）
SCIENCE_STYLE_ACTIVE = False


def setup_style():
    """
    设置全局 matplotlib + seaborn 样式。

    优先应用 SciencePlots 的 'science' 期刊风格（提升视觉期刊度）；
    若未安装 scienceplots 或风格加载失败，优雅降级到内置 rcParams 直设。
    降级策略确保无该依赖时团队仍可正常出图。
    """
    global SCIENCE_STYLE_ACTIVE
    applied_science = False

    # --- 尝试 SciencePlots 期刊风格（P0：视觉呈现升级） ---
    try:
        import scienceplots  # noqa: F401（注册 science 风格）
        # 优先用带网格的 'science' 变体；若 CJK 中文字体可用，附 'no-latex' 避免依赖 LaTeX
        style_list = ['science', 'grid']
        if _cjk_font:
            style_list.append('no-latex')
        plt.style.use(style_list)
        applied_science = True
    except Exception as e:
        print(f"[可视化] SciencePlots 未生效，使用内置样式回退: {e}")

    if applied_science:
        SCIENCE_STYLE_ACTIVE = True
        print("[可视化] 已应用 SciencePlots 'science' 期刊风格")
        # science 风格默认 font.family=['serif']，会迫使中文走 STIX 导致方框；
        # 强制 sans-serif 家族，令中文回落到 Microsoft YaHei。
        mpl.rcParams.update({
            'font.family': ['sans-serif'],
            'font.sans-serif': [_cjk_font, 'DejaVu Sans'] if _cjk_font else ['DejaVu Sans'],
            'axes.unicode_minus': False,
            'figure.dpi': 100,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight',
        })
        return

    # --- 降级分支：内置 rcParams 直设 ---
    sns.set_style("whitegrid")  # seaborn 全局样式
    mpl.rcParams.update({
        'font.sans-serif': [_cjk_font, 'DejaVu Sans'] if _cjk_font else ['DejaVu Sans'],
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.dpi': 100,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'lines.linewidth': 1.5,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
    })


def save_figure(fig, filename: str, formats: list = None):
    """
    保存图表为 PDF + PNG 双格式。
    
    Args:
        fig: matplotlib figure 对象
        filename: 不含扩展名的文件名
        formats: 保存格式列表，默认 ['pdf', 'png']
    """
    if formats is None:
        formats = ['pdf', 'png']
    
    for fmt in formats:
        path = f"{filename}.{fmt}"
        fig.savefig(path, dpi=300, bbox_inches='tight')
        print(f"✅ 图表已保存: {path}")


def plot_line(x, y_list, labels, xlabel="", ylabel="", title="",
              filename="figures/line_plot", grid=True):
    """
    绘制多条折线图。
    
    Args:
        x: x 轴数据
        y_list: y 轴数据列表 [y1, y2, ...]
        labels: 图例标签列表
        xlabel: x 轴标签
        ylabel: y 轴标签
        title: 图表标题
        filename: 保存路径（不含扩展名）
        grid: 是否显示网格
    """
    setup_style()
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    
    for i, y in enumerate(y_list):
        color = COLORS["palette"][i % len(COLORS["palette"])]
        style = LINE_STYLES[i % len(LINE_STYLES)]
        marker = MARKERS[i % len(MARKERS)]
        ax.plot(x, y, color=color, linestyle=style, marker=marker,
                markersize=4, markevery=max(1, len(x)//10), label=labels[i])
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if grid:
        ax.grid(True, alpha=0.3)
    ax.legend()
    
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_bar(categories, values, xlabel="", ylabel="", title="",
             filename="figures/bar_plot", horizontal=False, sort=True):
    """
    绘制柱状图。
    """
    setup_style()
    fig, ax = plt.subplots(figsize=SINGLE_COLUMN)
    
    if sort:
        idx = np.argsort(values)
        categories = [categories[i] for i in idx]
        values = [values[i] for i in idx]
    
    colors = [COLORS["palette"][i % len(COLORS["palette"])] for i in range(len(values))]
    
    if horizontal:
        ax.barh(categories, values, color=colors)
        ax.set_xlabel(ylabel)
        ax.set_ylabel(xlabel)
    else:
        ax.bar(categories, values, color=colors)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        plt.xticks(rotation=45, ha='right')
    
    ax.set_title(title)
    ax.grid(True, alpha=0.3, axis='y' if horizontal else 'x')
    
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_tornado(params, sensitivities, xlabel="目标值变化 (%)", title="灵敏度分析",
                 filename="figures/tornado"):
    """
    绘制 Tornado 图（参数敏感度排序）。
    
    Args:
        params: 参数名称列表
        sensitivities: 敏感度列表（正值表示目标值增加，负值表示减少）
    """
    setup_style()
    fig, ax = plt.subplots(figsize=DOUBLE_COLUMN)
    
    # 按绝对敏感度排序
    idx = np.argsort(np.abs(sensitivities))
    params = [params[i] for i in idx]
    sensitivities = [sensitivities[i] for i in idx]
    
    colors = [COLORS["primary"] if s > 0 else COLORS["quaternary"] for s in sensitivities]
    ax.barh(params, sensitivities, color=colors)
    
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3, axis='x')
    
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_scatter(x, y, labels=None, xlabel="", ylabel="", title="",
                 filename="figures/scatter_plot"):
    """绘制散点图"""
    setup_style()
    fig, ax = plt.subplots(figsize=SQUARE)
    
    ax.scatter(x, y, c=COLORS["primary"], alpha=0.6, s=30)
    
    if labels:
        for i, label in enumerate(labels):
            ax.annotate(label, (x[i], y[i]), fontsize=7, alpha=0.7)
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_heatmap(data, row_labels=None, col_labels=None, title="",
                 filename="figures/heatmap", cmap=None, annot=True, fmt=".2f"):
    """
    绘制热力图（seaborn 版）。

    Args:
        data: 2D 数组或 DataFrame
        row_labels: 行标签
        col_labels: 列标签
        cmap: 色板；None 时用 COLORMAPS["sequential"]（科学顺序色板，发散对比请显式传 COLORMAPS["diverging"]）
        annot: 是否在格子内标注数值
        fmt: 数值标注格式
    """
    if cmap is None:
        cmap = COLORMAPS["sequential"]
    setup_style()
    fig, ax = plt.subplots(figsize=SQUARE)

    # 标签为 None 时不显式传参，交由 seaborn 自动推断（传 None 会触发新版 seaborn 报错）
    heat_kw = dict(annot=annot, fmt=fmt, cmap=cmap, linewidths=0.5, ax=ax,
                   cbar_kws={"shrink": 0.8})
    if row_labels is not None:
        heat_kw["yticklabels"] = row_labels
    if col_labels is not None:
        heat_kw["xticklabels"] = col_labels
    sns.heatmap(data, **heat_kw)

    ax.set_title(title)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


# ============================================================
# Seaborn 专用封装函数
# ============================================================

def plot_boxplot(data, x=None, y=None, hue=None, xlabel="", ylabel="", title="",
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
    ax.set_title(title)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_violin(data, x=None, y=None, hue=None, xlabel="", ylabel="", title="",
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
    ax.set_title(title)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_distribution(data, x=None, kde=True, bins="auto", xlabel="", title="",
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
    ax.set_ylabel("频数")
    ax.set_title(title)
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_convergence(iterations, values, ylabel="目标值", title="收敛曲线",
                     filename="figures/convergence"):
    """
    绘制迭代收敛曲线（matplotlib，用于算法收敛性验证）。
    """
    return plot_line(
        iterations, [values], [""],
        xlabel="迭代次数", ylabel=ylabel, title=title,
        filename=filename, grid=True
    )


# ============================================================
# 纯可视化封装（只画，不算）
# ============================================================
# 以下函数只负责把"已由建模/求解层算好的数值"画对、画统一。
# 它们不承担任何统计计算（置信区间怎么算、蒙特卡洛怎么抽样、灵敏度怎么扰动
# 都是问题依赖的，必须由求解脚本按题目语义完成）。正确性由：
#   ① 输入数值（来自已验证的求解结果）  ② 函数内输入校验  ③ 单元测试 共同保证。

def plot_confint(x, y_mean, y_lower, y_upper, xlabel="", ylabel="", title="",
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
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    save_figure(fig, filename)
    plt.close(fig)
    return fig


def plot_errorbar(x, y, yerr=None, xerr=None, capsize=4, xlabel="", ylabel="",
                  title="", filename="figures/errorbar", color=None):
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
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    save_figure(fig, filename)
    plt.close(fig)
    return fig