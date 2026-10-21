# Paper Writer Playbook（CUMCM B）

> 角色流程以 `SKILL.md` 为准；本文件保留写作/修复的可执行细节。
> 完整旧版在 `legacy-paper-writer.md`；格式规范在 `latex-format.md`、`abstract-writing.md`、`deai-writing.md`、`artifact-registry.md`。

## 0. 先做 result_bundle 完整性反向核查（P0）

在写正文前，反向核对：

- `solution.json` 每个子问题是否有 `objective_value`/`decision_variables`/`solver`/`optimality`/`active_constraints`/`sensitivity`/`critical_points`/`monte_carlo`（opt）或 `task_type`/`metrics`/`model.selection`/`validation`/`preprocessing`/`data_lineage`（stats）。
- `modeling_plan.json`、`feature_fingerprint.json`、`术语表.json`、`handoff_notes_1.md`、`图表清单.md` 是否齐全。
- 缺字段 → 先报告 Lead，不自行补数；不得用“论文写法”掩盖缺失。

## 1. 论文结构（10 项）

摘要（≤1 页，四要素 + 定量结论）→ 问题重述 → 问题分析 → 模型假设（纯断言）→ 符号说明（单表）→ 模型建立与求解（按问题分节）→ 灵敏度/误差 → 模型评价与推广 → 参考文献 → 附录（完整可运行代码）。

## 2. 篇幅/合规红线

- 正文（摘要后、附录前）≥10 页且 ≤30 页；官方建议 20 页附近，冲高档次尽量压向 20。
- 摘要 ≤1 页。
- 图 ≥6 处引用；摘要候选 ≥2 版。
- 全文无学校/队员/赛区/导师信息；参考文献可查证；附录含完整可运行源程序。
- `shuwei_en`：Summary + 目录 + 正文 ≤25 页，不套 10–30 规则。

## 3. 写作规则

- 摘要按 `abstract-writing.md`：每问“做了什么 → 怎么算 → 得到什么数 → 说明什么”，结论定量。
- 去 AI 味按 `deai-writing.md`：少套话、少“首先/其次/最后”、多具体动词和数值；不写“综上所述”式空段。
- B 题特殊要求：决策/优化类必须有“决策依据 + 指标结果”，不能只列模型；图要驱动论证，不能一图多论点。
- LaTeX 按 `latex-format.md`：`ctex`/`xelatex`；图用 PDF；表用 booktabs；公式编号/符号一致；编译两遍消 `??`。
- 图表解析段每图 ≥150 字，先讲“图显示什么”，再讲“对结论意味着什么”；不重复 caption。
- 参考文献用可查证来源（DOI/出版社页面），不编造；不足 10 篇按实际可验证数并注明。

## 4. 编译

优先 `latexmk -xelatex`；MiKTeX 缺 perl 时用：

```powershell
xelatex -interaction=nonstopmode paper.tex
xelatex -interaction=nonstopmode paper.tex
```

编译失败按 `.log` 修；`paper.aux`/`paper.log` 是页数/摘要机查证据，不要删除（hygiene 已允许）。

## 5. 自审

- 页数/摘要：`paper.aux` 的 `abstract:end`、`appendix:start`。
- 图引用数、`\ref` 是否有 `??`、符号表与正文一致、术语表一致。
- 摘要候选写 `abstract_candidates.md`（≥2 版 + 取舍）。
- 交接写 `handoff_notes_2.md`（≤800 字 + 图表清单 + 完整性核查）。

## 6. R1/R2 修复

- 读 `review_report.json`、`fix_roundN.md`；逐条：接受修复 / 反驳 + 具体理由；写 `fix_roundN.md`（问题 → 处置 → 修复位置）。
- 修复涉及数值/移位 → 该小节全节数值重算，不只改单点。
- 建模根源错误 → 报告 Lead 标 `BLOCKED`，不自行改模型；图面缺陷交 Figures。
- 改完重编译，再 `pipeline_submit(stage="FIX_R1"|"FIX_R2", role="writer", produced_by="writer")`。

## 7. 禁止

- 改 `project/`、`solution.json`、`modeling_plan.json`、`result_bundle/figures/`、`run_state.json`。
- 重绘/Read 生成图；编造文献/数值；把 Q3/Q4 写成遗留项。
