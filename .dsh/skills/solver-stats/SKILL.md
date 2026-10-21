---
name: solver-stats
description: Use for the CUMCM-B data/statistics/simulation track. Reads the problem and data, builds and validates the model, writes project/ and result_bundle/, then submits MODELING. No figures, no paper, no method critique.
whenToUse: problem_track=stats and the current stage is MODELING (initial run or rework).
---

# Solver · stats 轨

你是本题的建模求解者。任务类型、模型、验证设计由你根据题面与数据决定；方法是可被批评的。

## 开始前

- **0. 题面覆盖核对（硬前置）**：读 `decision_logs/problem_coverage.json`（Lead 在 G0 产出）和 `赛题/题面.md` 全文。若 coverage 缺失，或 brief 覆盖的子问数 < 题面问题数，**立即报告 Lead 并停止**，不擅自开工。你的工作范围 = coverage 的全部子问，不是 brief 的前几问。
1. `pipeline_status(project_root, view="brief")`。
2. 读 `赛题/题面.md`（唯一题面入口）和全部附件数据；不要自行从 PDF 抽取。超过 1000 行不要全量读入，用 pandas 写规模/类型/缺失/±3σ/分布摘要。
3. 读本轨参考：`references/stats-playbook.md`。
4. 读 `references/data-conventions.md`、`references/data-decision-tree.md`、`references/method-cards/`、`references/paper-index.md`。
5. 若 `rework.active`：
   - `mode=resume`：只改 `rework_brief.change`；`keep` 不得重开。
   - `mode=fresh_dossier`：读 `failure_dossier.json`；**先写 `rework_plan.json`**，过计划门再写代码；旧产物只作负证据。
   - 不改 `rework_brief` / `failure_dossier` / `run_state.json`。

## 交付路径

- `result_bundle/solution.json`：按 `AGENTS.md` handoff 契约的 stats 字段（task_type、objective_or_goal、metrics、model.selection（含基线）、validation（含 overfitting_check）、preprocessing（含 train_test_isolation）、data_lineage、sensitivity、monte_carlo）。
- `result_bundle/modeling_plan.json`、`feature_fingerprint.json`（用 stats 模板）、`术语表.json`。
- `project/` 下可运行代码；`project/results/*.json`。
- `handoff_notes_1.md`（≤800 字）。
- fresh_dossier 返工另交 `decision_logs/rework_plan.json`。

## 提交前自检

```powershell
.venv\Scripts\python.exe .trae\code_templates\check_solution_json_stats.py result_bundle/solution.json project/results --selfcheck
.venv\Scripts\python.exe .trae\code_templates\check_leakage.py project
.venv\Scripts\python.exe .trae\code_templates\check_modeling_artifacts.py <项目根> --scope modeling
```

`check_leakage` 只报 WARN，不因此停；ERROR 先修。再加一条**覆盖自检**：

- `solution.json` 必须对 `decision_logs/problem_coverage.json` 的每个 `questions[].id` 有对应条目/字段；缺一问 = ERROR，补完再提交。
- 若 run 没有 coverage（Phase 2B 之前的旧 run），从题面全文自行列出全部子问并在 handoff 中报告，不得默认只做前两问。

然后：

```text
pipeline_submit(stage="MODELING", role="solver", produced_by="solver", summary="...")
```

## 禁止

- 不得跳过验证设计、过拟合自查、灵敏度分析、基线对比。
- 不得在全数据上拟合预处理或调参后再划分；时序/分组禁止随机划分。
- 不得伪造指标、泄漏检查结果、蒙特卡洛结果。
- 不得出图、不得写 `result_bundle/figures/`。
- 不得写 `method_critique`、论文、`run_state.json`、`pipeline_state.json`。
