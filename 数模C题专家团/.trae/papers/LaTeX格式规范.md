# LaTeX 格式规范（CUMCM 论文）

> 用途：Agent 2 阶段 4 论文写作排版规范。所有 CUMCM 论文必须严格遵循。

---

## 一、文档基础设置

```latex
\documentclass[12pt,a4paper]{ctexart}

% === 页面布局 ===
\usepackage[top=2.54cm, bottom=2.54cm, left=3.18cm, right=3.18cm]{geometry}

% === 行距 ===
\usepackage{setspace}
\linespread{1.5}

% === 字体 ===
\setCJKmainfont{SimSun}[AutoFakeBold=2.5]          % 正文：宋体小四号
\setCJKsansfont{SimHei}                              % 无衬线：黑体
\setCJKmonofont{SimSun}                              % 等宽：宋体

% === 标题格式 ===
\ctexset{
  section = {
    format = \zihao{3}\heiti\centering,              % 一级标题：黑体三号加粗居中
    aftername = \quad
  },
  subsection = {
    format = \zihao{4}\heiti,                        % 二级标题：黑体四号加粗
    aftername = \quad
  },
  subsubsection = {
    format = \zihao{-4}\heiti,                       % 三级标题：黑体小四号加粗
    aftername = \quad
  }
}

% === 必备宏包 ===
\usepackage{amsmath,amssymb,amsthm}    % 数学公式
\usepackage{booktabs}                  % 三线表
\usepackage{graphicx}                  % 插图
\usepackage{float}                     % 浮动体控制
\usepackage{hyperref}                  % 超链接
\usepackage{caption}                   % 图表标题
\usepackage{enumitem}                  % 列表
\usepackage{algorithm,algpseudocode}   % 算法伪代码
% === 参考文献 GB/T 7714 ===
\usepackage[sort&compress]{gbt7714}    % 参考文献 GB/T 7714
```

**两条结构红线（官方规范，违反直接扣分）**：

1. **禁止 `\tableofcontents`**——官方明确"不要目录"，目录白白占用正文页数。
2. **摘要页不使用 `\maketitle`**（会带入队名/日期，且不符合惯例）——摘要页只含：论文标题（黑体三号居中）+ 摘要正文 + 关键词，一页以内。

---

## 二、字体规范

| 元素 | 字体 | 字号 | 加粗 |
|------|------|:---:|:---:|
| 正文 | 宋体 (SimSun) | 小四号 | 否 |
| 一级标题 | 黑体 (SimHei) | 三号 | 是 |
| 二级标题 | 黑体 (SimHei) | 四号 | 是 |
| 三级标题 | 黑体 (SimHei) | 小四号 | 是 |
| 图表标题 | 宋体 (SimSun) | 五号 | 否 |
| 表格内容 | 宋体 (SimSun) | 五号 | 否 |
| 页眉页脚 | 宋体 (SimSun) | 五号 | 否 |
| 参考文献 | 宋体 (SimSun) | 五号 | 否 |

---

## 三、标题编号

```
1    一级标题（黑体三号加粗居中）
1.1  二级标题（黑体四号加粗）
1.1.1 三级标题（黑体小四号加粗）
```

---

## 四、表格规范

**强制使用三线表**：

```latex
\begin{table}[H]
  \centering
  \caption{表格标题}
  \label{tab:xxx}
  \begin{tabular}{ccc}
    \toprule
    列1 & 列2 & 列3 \\
    \midrule
    数据 & 数据 & 数据 \\
    \bottomrule
  \end{tabular}
\end{table}
```

规则：
- 使用 `\toprule` / `\midrule` / `\bottomrule`（booktabs 宏包）
- 禁止使用竖线 `|` 分隔列
- 表格标题在表格上方
- 表格内容五号宋体
- 表格在文中必须有 `\ref{tab:xxx}` 引用

---

## 五、公式规范

```latex
% 行内公式
$x_i \in [0, 1]$

% 行间公式（编号）
\begin{equation}
  \min \sum_{i=1}^{n} c_i x_i
  \label{eq:objective}
\end{equation}

% 多行公式
\begin{align}
  \sum_{j=1}^{m} x_{ij} &= 1, \quad \forall i \label{eq:assign1} \\
  \sum_{i=1}^{n} x_{ij} &\leq 1, \quad \forall j \label{eq:assign2}
\end{align}
```

规则：
- 公式编号：`(1)` `(2)` ... 或章节式 `(1.1)` `(1.2)`
- 变量首次出现需解释含义
- 向量/矩阵用粗体：`\mathbf{x}`
- 期望用 `\mathbb{E}`，概率用 `\mathbb{P}`

---

## 六、图表规范

```latex
% 单图
\begin{figure}[H]
  \centering
  \includegraphics[width=0.8\textwidth]{figures/xxx.pdf}
  \caption{图片标题}
  \label{fig:xxx}
\end{figure}

% 双图并排
\begin{figure}[H]
  \centering
  \begin{minipage}{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{figures/xxx_a.pdf}
    \caption{子图 A 标题}
    \label{fig:xxx_a}
  \end{minipage}
  \hfill
  \begin{minipage}{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{figures/xxx_b.pdf}
    \caption{子图 B 标题}
    \label{fig:xxx_b}
  \end{minipage}
\end{figure}
```

规则：
- 优先使用 PDF 矢量图（其次 PNG 300dpi）
- 图片标题在图片下方
- 每张图表在文中必须有 `\ref{}` 引用
- 禁止出现"如图X所示"而无分析段落
- 每张图表配 ≥150 字独立解析段落

---

## 七、参考文献规范

```latex
% 使用 GB/T 7714 格式
\bibliographystyle{gbt7714-numerical}
\bibliography{references}
```

规则：
- ≥10 篇，GB/T 7714 格式
- 含 ≥3 外文文献 + ≥5 期刊文献
- 引用格式：`\cite{key}` 产生上标 `[1]`
- 参考文献表五号宋体

---

## 八、编译命令

```bash
xelatex -interaction=nonstopmode paper.tex
xelatex -interaction=nonstopmode paper.tex   # 两次编译（生成目录/交叉引用）
```

**禁止使用 `pdflatex`**（不支持中文）。

---

## 九、常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 中文显示为空白 | 未用 xelatex 编译 | 改用 xelatex |
| 字体缺失 | 系统无 SimSun/SimHei | Windows 自带，Linux 需安装 |
| 参考文献 [?] | 未编译两次 | 再跑一次 xelatex |
| 表格超宽 | 列数过多 | 使用 `\small` 缩小字号或 `tabularx` |

---

## 十、合规要点（官方格式规范硬约束，编译前逐项核对）

1. **摘要 ≤1 页**（含标题和关键词，无需英文翻译），摘要页起编页码（页脚居中，从"1"开始）。
2. **正文尽量 ≤28 页**（摘要页之后起算，不要目录；官方表述为"尽量控制在 20 页以内"，28 页为本团队内部宽松上限，超页须用户决断）。**附录页数不限**。
3. **匿名性**：摘要页、正文、附录（含图表、代码注释）任何位置不得出现参赛者身份、学校、赛区信息。
4. **附录必含**：全部完整、可运行的源程序代码 + 支撑材料文件列表（缺可运行程序或程序结果与论文不符可取消评奖资格）。
5. **参考文献**：引用他人成果必须规范列出并在正文标注。
6. 页边距上下左右至少 2.5cm（官方要求）；字号字体行距官方不统一规定，按本规范前述条款执行。
7. 若当年组委会提供官方模板，优先使用官方模板，本规范仅作补充。