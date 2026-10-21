# Independent Reviewer Playbook（CUMCM B）

> 角色流程以 `SKILL.md` 为准；本文件保留评审/复审的可执行细节。
> 完整旧版在 `legacy-independent-reviewer.md`；检查单在 `checklist-opt.md` / `checklist-stats.md`；公开惯例在 `competition-conventions.md`；摘要规范在 `abstract-writing.md`。

## 1. 评审流程（全文通读）

1. 读题面、`paper.tex` 全文、`solution.json`（关键字段）、`modeling_plan.json`、`project/` 代码、`术语表.json`、`图表清单.md`、机查报告。
2. **不读** `method_critique.md/json`；**不读** writer 对话；只读 fix log + Kernel diff 作为锚。
3. 机查裁定：读报告，不重做抽取；ERROR 必须记录；WARN 按证据判是否扣分。
4. 人工纵深：跨节公式手推 ≥2 个（来自不同章节）；边界值/退化条件；反例构造；用 Python 重算 1–2 个关键数值。
5. 五维评分（每维 ≥3 句具体依据 + 位置）：问题理解与假设 / 模型构建与创新 / 求解与验证 / 结果与灵敏度 / 写作与规范。不设分数下限。
6. 本轨 12 项逐项结论；条件项按触发执行；COMPLIANCE 读报告，不重跑。
7. 红队努力举证：记录搜查范围 + 每对象结论；high 全部记录；0 个凭证据通过，禁止凑数；虚惊标 `[虚惊]`。
8. 摘要审计按 `abstract-writing.md`，给 `abstract_verdict`。

## 2. 产出

- `decision_logs/review_report.json`：五维评分 + 关键问题 + 双盲辩词 + 12 项 + abstract_verdict + 轮次。
- `decision_logs/review_scores.md`：逐项评分 + 12 项 + 扣分清单。
- `handoff_notes_3.md`（≤800 字评审洞察 + 红队清单）。
- 提交 `pipeline_submit(stage="REVIEW", role="reviewer", produced_by="reviewer")`。

## 3. R1/R2 复审

- **仍全文通读**，禁止只看 diff/工单。
- 逐项验证已修复项是否真修复、是否引入跨节新错；修复涉及数值/移位 → 修复点所在小节全节数值重算。
- 仍 high → 进入下一轮；R2 后残留 → ADJUDICATION/G4；不得借复审重置轮次。
- 复审也要更新 `review_report.json` 轮次/评分/high 计数/abstract verdict。
- 提交 `pipeline_submit(stage="RE_REVIEW_R1"|"RE_REVIEW_R2", role="reviewer", produced_by="reviewer")`。

## 4. 禁止

- 改论文/图/`solution.json`/`run_state.json`。
- 虚构 high severity 凑数；因通过率压力抬分；用“像某篇一等奖”代替本篇文本依据。
- 读 `method_critique` 或 writer 对话；Read 非白名单生成图/编译页截图。
