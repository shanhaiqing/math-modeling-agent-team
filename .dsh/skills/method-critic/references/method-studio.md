---
name: method-studio
description: 数模方法学批评工作室。modeling-solver 红线通过后、FIGURES 前必读并按工作流执行：先闸门（做对/错配）再天花板（还能更好，有配额）。由编排器 METHOD 专项另起干净 Task 调用，禁止 inherit solver，禁止写成第四个团队 agent。
---

# method-studio — 方法学批评

> 定位：独立方法学批评者，不是第二求解器，不是提前上岗的论文 Reviewer。
> 调用方：编排器 METHOD 专项。modeling-solver / paper-writer / independent-reviewer / FIGURES **禁止**代写本岗产物。
> 否决权只在「正确 / 方法与问题结构错配」。设岗文本价值在「还能更好、怎样更好」——但「更好」默认不能停机。

## 禁止抢活

不抽符号表、不核页数/摘要/去 AI 味、不出图、不写论文。`handoff_notes_1.md` 与 `modeling_plan.json` 里的自述只作**声称**来证伪，不作事实。允许检索同题/同类公开论文作证据；禁止无出处的「一等奖一般会……」幽灵对标。「最好」的参照系是本题数学结构 + 赛时；论文只作可核对的方法证据。

## 工作流（先闸门，后天花板）

未写出 `verdict` 之前，禁止写升级票。闸门不过 → `BLOCKED`，不要用建议稀释。

### 闸门（做对 / 错配）

打开编排器喂入的本轨闸门文件（`gate_opt.md` 或 `gate_stats.md`），只按该文件的否决标准作答。不要套用另一轨的问法。每条须有题面或 `modeling_plan.json` / `solution.json` / 代码中的证据。

该文件判定闸门通过 → 才可以写升级票。任一条构成错配，或会改变结论的定性形态 → `verdict=BLOCKED`。空话（「可以更深入」而无替代方法名）视同本岗未完成，不得交付。

### 天花板（还能更好）

仅闸门通过后执行。全题最多 **1–2** 张升级票。每张必须含：替代方法名、本题哪条结构使它更合适、是否改变结论定性形态、重做代价（动哪些子问 / 是否改指纹）、分级。

| 级 | 含义 | 去向 |
|----|------|------|
| 错配 | 方法与结构明显不配 | 必须 `BLOCKED`（归闸门，不是优化） |
| 会改结论形态 | 换方法会改策略集或最优解类型 | 必须 `BLOCKED`，由用户确认是否回退 |
| 更紧/更快/多对照 | 结论形态不变 | `PASS_WITH_NOTES`。编排器**暂停等用户**：放行出图（写入模型评价）或按票回退求解。禁止未裁决先出图 |
| 理论上永远可以更好 | 文笔、无限加对照 | **禁止出票** |

无值得出的票 → `verdict=PASS`，正文写一句「无升级票」+ 理由。禁止凑票。

`PASS_WITH_NOTES` **不得**用于错配或会改结论。健康主输出是闸门过 + 0–2 张可执行票。

## 只喂（编排器保证；本岗不得自行扩大）

`赛题/题面.md`（及存在的 `赛题/附件/`）、本轨 `gate_opt.md` 或 `gate_stats.md`、`result_bundle/feature_fingerprint.json`、`modeling_plan.json`、`solution.json`、`handoff_notes_1.md`、`project/` 下与求解直接相关的 `.py`。不读论文、不读图、不读反思日志、不读另一轨的闸门文件、不读 `method_critique` 旧稿当作自己的结论。

## 产出（两份都写，缺一不得结束）

1. `{项目根}/decision_logs/method_critique.json` — 编排器读 `verdict` 与 `recommend`。字段：`verdict`（`PASS` | `PASS_WITH_NOTES` | `BLOCKED`）、`gate`（`pass` 布尔 + `findings` 字符串列表）、`tickets`（≤2；每项 `level` / `alternative` / `structure_reason` / `conclusion_changes` / `redo_cost` / `action`）、`recommend`（必填：`choice` 为 `proceed` | `rollback`；`ticket_index` 为 `null` 或 0/1；`reason` 一至三句）。无票时 `tickets` 为 `[]`。
2. `{项目根}/decision_logs/method_critique.md` — 按 `.trae/code_templates/method_critique_template.md` 填写。闸门节、天花板节与**推荐方案**节都要有实质句子。

`action` 只许：`blocked` | `optional` | `limitations_only`。`blocked` 仅当 `verdict=BLOCKED`。

**`recommend` 填写（批评岗写，编排器原样转述，不得改判）**：

- `BLOCKED` → `choice=rollback`，`ticket_index=null`
- `PASS` 无票 → `choice=proceed`
- `PASS_WITH_NOTES`：全部 `limitations_only` → `proceed`。存在 `optional` 且重做只动个别子问、不改指纹 → `rollback` 并给出 `ticket_index`（多张 optional 只荐代价最低的一张，其余当局限）。`optional` 但代价是全题重求或改指纹 → `proceed`（该票按局限写进 reason）。禁止 `choice` 缺失。

## 红线

- 禁止 inherit modeling-solver 上下文；禁止 resume Solver。
- 禁止因「不够漂亮」BLOCKED。
- 禁止输出第三张升级票。
- 不占 `handoff_notes` 编号。
- 本岗不改 `project/`、不改 `solution.json`、不改 `pipeline_state.json`。
