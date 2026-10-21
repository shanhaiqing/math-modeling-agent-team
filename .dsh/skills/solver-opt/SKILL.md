---
name: solver-opt
description: Use for the CUMCM-B optimization/operations-research track. Reads the problem, builds the model, solves and validates it, writes project/ and result_bundle/, then submits MODELING. No figures, no paper, no method critique.
whenToUse: problem_track=opt and the current stage is MODELING (initial run or rework).
---

# Solver · opt 轨

你是本题的建模求解者。结构、算法、参数由你根据题面决定；方法是可被批评的，不是不可质疑的。

## 开始前

- **0. 题面覆盖核对（硬前置）**：读 `decision_logs/problem_coverage.json`（Lead 在 G0 产出）和 `赛题/题面.md` 全文。若 coverage 缺失，或 brief 覆盖的子问数 < 题面问题数，**立即报告 Lead 并停止**，不擅自开工。你的工作范围 = coverage 的全部子问，不是 brief 的前几问。
1. `pipeline_status(project_root, view="brief")`。
2. 读 `赛题/题面.md`（唯一题面入口）和全部附件数据；不要自行从 PDF 抽取。
3. 读本轨参考：`references/opt-playbook.md`。
4. 读 `references/optimization-conventions.md`、`references/optimization-decision-tree.md`、`references/method-cards/`、`references/paper-index.md`。
5. 若 `rework.active`：
   - `mode=resume`：只改 `decision_logs/rework_brief.json` 的 `change`；`keep` 不得重开。
   - `mode=fresh_dossier`：读 `decision_logs/failure_dossier.json`；**先写 `decision_logs/rework_plan.json`**，等 Kernel 计划门通过后再写代码。旧产物在 `attic_paths` 里只作负证据，不作起点。
   - 任何模式都不要改 `rework_brief` / `failure_dossier` / `run_state.json`。

## 交付路径

- `result_bundle/solution.json`：按 `AGENTS.md` handoff 契约的 opt 字段（objective_value、decision_variables、solver、optimality、active_constraints、sensitivity、critical_points、monte_carlo）。
- `result_bundle/modeling_plan.json`、`feature_fingerprint.json`（用 `feature_fingerprint_template_opt.json`）、`术语表.json`。
- `project/` 下可运行代码；`project/results/*.json`。
- `handoff_notes_1.md`（≤800 字，质疑点分「论文讨论项」/「建模遗留项」）。
- fresh_dossier 返工另交 `decision_logs/rework_plan.json`。

## 提交前自检

```powershell
.venv\Scripts\python.exe tools\checks\check_solution_json.py result_bundle/solution.json project/results --selfcheck
.venv\Scripts\python.exe tools\checks\check_modeling_artifacts.py <项目根> --scope modeling
```

ERROR 先修；WARN 记录。再加一条**覆盖自检**：

- `solution.json` 必须对 `decision_logs/problem_coverage.json` 的每个 `questions[].id` 有对应条目/字段；缺一问 = ERROR，补完再提交。
- 若 run 没有 coverage（Phase 2B 之前的旧 run），从题面全文自行列出全部子问并在 handoff 中报告，不得默认只做前两问。

然后：

```text
pipeline_submit(stage="MODELING", role="solver", produced_by="solver", summary="...")
```

提交失败就按 findings 修，再提交；不要声称通过。

## 禁止

- 不得跳过最优性验证、模型验证、灵敏度分析、临界点/多算例。
- 不得伪造 MIPGap、临界点、蒙特卡洛结果。
- 不得出图、不得写 `result_bundle/figures/`。
- 不得写 `method_critique`、论文、`run_state.json`、`pipeline_state.json`。
- 不得把同题专有符号/数据写入 `tools/checks/` 或技能 references。
