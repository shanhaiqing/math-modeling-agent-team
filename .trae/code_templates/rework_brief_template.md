# 建模返工单

> 编排器在再次调用 modeling-solver **之前**写入。solver 只读、禁止改本文件。不占 handoff_notes 编号。
> 磁盘上有本文件 ≠ 返工：仅当本次调用的上游产出清单列出 `decision_logs/rework_brief.md` 时，solver 才走返工模式。
> Schema 与 `rework_brief_template.json` 一致；JSON 为机查源，本文给执行岗读。

**active**：与 `pipeline_state.json` 的 `rework_brief_active` 同时为 true 时本单为当前工单。modeling 红线通过后编排器将 active 置 false；文件可留作审计。再次回退则整份覆盖，禁止 `rework_brief_2` 一类编号。

**trigger**：`METHOD_TICKET` / `METHOD_BLOCKED` / `HG1` / `WRITER_BLOCKED` / `REVIEW_BLOCKED` / `USER`

**ticket_index**：无票或非按票回退则 `null`；按 METHOD 升级票回退则 0 或 1（与 `method_critique.json` 的 `tickets` 下标一致）。编排器从批评稿或用户原文组装，**不得改判**。

## 必须保留（keep）

- （子问 / 指纹字段 / 数值——本轮不得当新题重开）

## 必须改变（change）

- （主方法 / 子问 / 须覆盖的 `solution.json` 字段）

## 禁止（forbidden）

- resume 被否方法
- 把现有 `solution.json` 当本阶段已完成

## 必读（must_read）

- `赛题/题面.md`
- `decision_logs/rework_brief.md`

## 用户裁决（user_decision）

（确认回退的原话或票号，一两句）
