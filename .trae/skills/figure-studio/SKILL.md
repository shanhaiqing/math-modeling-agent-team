---
name: figure-studio
description: 数模论文图表工作室。凡涉及出图/修图/重绘图（求解配图、灵敏度图、框架图、示意图、图面修复）时必读并按其工作流执行：设计卡先行 → 选型 → hero 图指定 → 绘制（配方/样式）→ 程序自检 → 导出登记。感知层交 HG1 人工，禁止模型 Read 生成图。
---

# figure-studio — 数模论文图表工作室

> 定位：不是绘图工具说明，而是**出图工作流**。跳过设计卡直接写代码 = 产出平庸图的根因。
> 调用方：编排器 FIGURES 专项（modeling-solver / paper-writer / independent-reviewer **禁止**出图或 Read 生成图）。
> 配套资产：选型判据见 `.trae/papers/图表类型参考库.md`；样式函数见 `.trae/code_templates/visualization_style.py`。

## 通道规则（先选通道，再动手）

| 图的性质 | 通道 | 工具 |
|---|---|---|
| 有数值轴（数据图：折线/柱状/散点/热力/分布…） | 数据图通道 | matplotlib + `visualization_style.py` + `recipes/` |
| 框+箭头（框架图/流程图/技术路线图） | 框架图通道 | `recipes/tikz_swimlane.tex`（standalone 编译→`\includegraphics`） |
| 机理/几何/物理关系示意图 | 示意图通道 | `recipes/tikz_schematic.tex`（同上） |

**禁止**：用 matplotlib 硬画框+箭头流程图（必然平庸）；用 AI 生图工具产论文图（不可复现，竞赛纪律红线）。

## 工作流（6 步，每图一遍；步骤 0 不可跳过）

0. **设计卡**（判据 `references/figure_design.md`）：先写一句话"This figure shows that ___"——写不出此句的图不画；确定编码映射（x/y/颜色/大小/分面各映射什么，**颜色必须编码一个维度而非装饰**）与正文引用位置。**设计卡必填图幅三字段**：①面板数与布局（2 面板横排、3 面板横排仅精简内容、≥4 面板 2×2 网格）②canvas 尺寸（总宽锁定 `CU_TEXTWIDTH_IN`≈5.75in=0.9\textwidth，行高按面板宽高比 4:3）③折算后最小字号（每面板展示宽=栏宽÷横排面板数，图内最小字 ≥ 正文字号 70%，正文 12pt → ≥9pt）。绘制前读 `{项目根}/赛题/题面.md`；示意图/几何题可读 `赛题/题面图/`（题面源图，禁止 Read 论文生成图）。
1. **选型**：查 `.trae/papers/图表类型参考库.md` 决策表；有配方（`recipes/`）优先用配方。
2. **hero 指定**：全篇指定 1-2 张 hero 图（核心论证图），hero 图投入 ≥3 倍于普通图的打磨。
3. **绘制**：**figsize 按最终展示尺寸设定——canvas 总宽锁定 `CU_TEXTWIDTH_IN`（0.9\textwidth≈14.6cm），与论文 includegraphics 1:1，禁止导出后缩放**（matplotlib 字号是绝对单位，缩放即失真）；多面板用 `new_figure`（自动网格布局与面板行高）；每图含单位/图例/n/误差交代。
4. **程序自检**（零 token）：绘图代码末尾调用 `scripts/visual_qa.py` 的 `audit_figure(fig)`——缺字形/文本裁切/刻度重叠，ERROR 未清零禁止导出。这不是模型看图。
5. **导出登记**：PDF+PNG(300dpi) 双格式（`save_figure`），文件名入 `result_bundle/图表清单.md`（编号/claim/数据来源字段/生成脚本）。**禁止 Read 渲染出的 PNG/PDF**。感知层（遮挡/对齐/字号/claim 是否成立）交 HG1 人工看 PNG；hero 四轴同交 HG1。

## 生产端契约

每子问题 ≥2 图、总数 ≥6 含 ≥1 流程图、**图表类型 ≥3 种**、禁凑数。消费方为 paper-writer 图表类型分配与 reviewer 5d（文本核验）/ HG1–HG2 人工看图。

## 红线（不可协商）

- **可复现**：每图必由脚本从数据文件生成，禁止手贴数据、禁止 AI 生图。
- **数值可溯源**：图上每个数可回溯到 solution.json / 数据文件，溯源不了的数不上图。
- **图内不放中文大标题**：标题职能由论文 `\caption` 承担（图内标题+caption 双标题=冗余缺陷）。
- **一张图一个核心结论**：一图塞多个论点 → 拆图。
- **求解器结果直接引用**：图内统计量从 results JSON 读取，禁止人工转录。
- **禁止模型读图**：不得 `Read` 生成 PNG/PDF/WebP；不得用视觉循环回改。观感缺陷等人在 HG1 指出后再改脚本重渲。

## 资产索引

| 资产 | 路径 | 何时读 |
|---|---|---|
| 设计卡判据 | `references/figure_design.md` | 步骤 0 必读 |
| 程序自检与人工感知层清单 | `references/visual_review.md` | 步骤 4 必读（程序层）；感知层交 HG1 |
| TikZ 框架/示意图规范 | `references/tikz_heroes.md` | 走 TikZ 通道前必读 |
| 程序自检 | `scripts/visual_qa.py` | 步骤 4 调用；机查可 `scan` 目录 |
| 联合分布图配方 | `recipes/joint_plot.py` | 双变量关系+第三维演化 |
| 山脊图配方 | `recipes/ridgeline.py` | 3-6 组分布形态对比 |
| 瀑布图配方 | `recipes/waterfall.py` | 基线→最终值逐项增减分解（成本归因） |
| 平行坐标图配方 | `recipes/parallel_coords.py` | 多目标 Pareto 解集 trade-off |
| 雨云图配方 | `recipes/raincloud.py` | 分布+散点+箱线三合一（小样本） |
| 泳道框架图模板 | `recipes/tikz_swimlane.tex` | 模型框架图/技术路线图 |
| 概念示意图模板 | `recipes/tikz_schematic.tex` | 机理/几何/物理关系 |
