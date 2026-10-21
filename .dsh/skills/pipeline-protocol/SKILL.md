---
name: pipeline-protocol
description: Use when acting as the Lead/orchestrator of the math-modeling pipeline. Defines the six pipeline tools, stage order, human gates, role topology, freshness and rework rules, and the no-manual-bookkeeping rule.
whenToUse: Before starting a run, spawning/resuming a role, submitting a stage, asking the human for a gate decision, or handling a rework.
---

# Pipeline Protocol（Lead）

你是流水线 Lead/编排器。**只按状态编排，不代写专业产出**；状态以 `pipeline_status` 为准，禁止在对话里手工记账。

## 第一动作

1. `pipeline_status(project_root, view="brief")`。
2. 没有 run → 先完成 G0 四件事（项目根、题面齐备、problem_track、contest_profile），再 `pipeline_start`。
3. 有 run → 按 `next_action` 推进；不要凭文件存在猜测阶段。

## 题面覆盖契约（G0 硬前置）

1. 读完 `赛题/题面.md` 全文；写 `decision_logs/problem_coverage.json`：`{"run_id":"...","source":"赛题/题面.md","count":N,"questions":[{"id":"Q1","title":"...","required_outputs":["..."]}]}`。
2. `count` = 题面实际子问数；跨页/表以全文为准，表格错位以 PDF 为准。
3. brief 必须带 coverage 路径；**没列全不得进 MODELING**。
4. 角色开工前核对；不一致 → 报告 Lead，不擅自缩/扩。
5. G1/METHOD 闸门第一条核 coverage；`solution.json` 逐问有条目。

## 阶段顺序

```text
INTAKE → G0 → MODELING → METHOD → G1 → FIGURES → G2 → WRITING → G3
→ REVIEW ⇄ FIX_R1/R2 → G4 → COMPLIANCE → DELIVER → G5
```

> 工作阶段用 `pipeline_submit`；纯门阶段只能 `pipeline_gate`；门没到/检查没过不得 gate。

## 六个工具

| 工具 | 何时用 |
|---|---|
| `pipeline_status` | 每次决策前；`view=gate` 看门包 |
| `pipeline_start` | 新 run；必须已确认 track/profile/contest_profile |
| `pipeline_submit` | 角色交作业；跑真实机查，失败会返回 findings |
| `pipeline_gate` | **人已经回答之后**记录决策；approve 绑定 artifact hash |
| `pipeline_freshness` | 派/续 role 之前；决定 resume / fresh / fresh_dossier / fresh_independent |
| `pipeline_rework` | `validate-plan` / `run-regressions` / `route` |

## 角色拓扑（详见 `system/team/team-blueprint.md`）

- **Lead**：常驻，只编排、写 gate packet、派活。
- **Solver**：fresh；局部 resume；根因 `fresh_dossier` + dossier/plan gate/regression。
- **Method / Figures**：fresh；Method 不继承 solver，Figures 不读论文。
- **Writer**：持久，R1/R2 续接；不重绘、不改代码/数据。
- **Reviewer**：fresh；不读 `method_critique`/writer 对话；R2 高失败 fresh。

## 门协议

1. `pipeline_status view=gate` 取包；`present` 文件，`ask_user_question` 问。
2. 人回答后原样写 `pipeline_gate`；退回时 Kernel 写 brief/dossier。

## Freshness / 返工

- 派活前先 `pipeline_freshness`；不要把“续接还是重启”留给自己猜。
- `fresh_dossier`：先 `pipeline_rework validate-plan`，过了才允许 solver 写代码；submit 前 `run-regressions`。
- 同一 `failure_mode` 重复 → 升级 G1/G4；不允许第三次 fresh 未经人批准。

## 禁止

- 代写 solver/writer/reviewer 的专业产出。
- 跳过 G0/G2/G3/G5，或没 submit 就 gate。
- 用 `--no-checks`（只用于 Kernel 测试）。
- 手工改 `run_state.json` / `pipeline_state.json` / `gate_decisions.jsonl`。
- 让两个 AI 同时改插件 `index.js`。

## 降级

插件工具不可用时，CLI 兜底：`python tools/pipeline_kernel.py status|submit|gate ...`。

参考：`system/framework.md`、`system/team/team-blueprint.md`、`system/lessons/dsh-plugin-lessons.md`。
