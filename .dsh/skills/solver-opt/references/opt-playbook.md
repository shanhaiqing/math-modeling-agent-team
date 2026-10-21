# Opt 轨建模求解 Playbook

> 这是 `solver-opt` 的领域参考。角色流程以 `SKILL.md` 为准；本文件保留可直接执行的方法与交付细节。
> 完整旧版角色文本在 `legacy-solver-opt.md`；方法库在 `method-cards/` 与 `optimization-decision-tree.md`。

## 1. 先定结构，再选算法

1. 读 `赛题/题面.md`，再读附件数据；禁止自行从 PDF 抽取题面。
2. 读 `optimization-decision-tree.md`、`method-cards/`、`paper-index.md`；方法卡是可以否决的库，不必逐张写匹配矩阵。
3. 在 `feature_fingerprint.json` 里写 `problem_type`（LP/IP/MIP/NLP/DP/Network/Other）；MOO、博弈写 `overlays`，不覆盖主类型。
4. 在 `modeling_plan.json` 写 `design_critique`、`source_parameters`、`indicator_dimension_check`；适用时写 `cost_decomposition`、`alternative_algorithm_discussion`、`joint_constraint_check`、`multi_model_candidates`。
5. 简化假设若可能改变结果量级（≥10%），在 `design_critique` 写含/不含对照，并说明为何仍采用。

## 2. 交付字段

- `result_bundle/solution.json`：每个子问题必须有 `objective_value`、`decision_variables`、`solver`、`optimality`、`active_constraints`（active/slack + 派生量）、`sensitivity`、`critical_points`（含 source）、`monte_carlo`（不适用则 null 并说明）。
- `result_bundle/modeling_plan.json`：上述计划字段；`source_parameters` 逐字抄题面数值。
- `result_bundle/feature_fingerprint.json`：按 `feature_fingerprint_template_opt.json` 的字段/枚举。
- `result_bundle/术语表.json`：`symbol`、`meaning`、`unit`、`economic_interpretation`、`source`、`cross_reference`。
- `project/问题X_求解.py`、`project/results/*.json`。
- `handoff_notes_1.md`（≤800 字；质疑点分「论文讨论项」/「建模遗留项」）。

## 3. 求解器优先级（不可颠倒）

1. MIP/IP/LP → `mip_solver.py` / `solver_backend.py`
2. `linearized=true` → 仍走 MIP
3. CP-SAT → `cp_solver.py`（仅调度/纯约束满足，且说明为何不用 MIP）
4. NLP → `nlp_solver.py`（仅不可线性化）
5. 纯网络 → `graph_utils.py`（可辅以 MIP）
6. 元启发式 → `metaheuristic_solver.py`（仅规模大且精确求解超时/不可行；禁止因“NP-hard”一上来就用遗传算法）
7. 自实现 → DP 填表/排队解析

蒙特卡洛用 `monte_carlo_template.py`。禁止商业求解器。MIPGap/status 取求解器原生状态；`optimal` 即 gap=0；时限中断要么延长时间、要么做规模校验，禁止伪造 gap。启发式至少 5 次独立运行，报最优/平均/标准差。模板只改 PARAMETERS，不改 CORE ALGORITHM。

## 4. 验证必须真做

- 最优性：MIPGap、枚举完备性或启发式统计；不能只在散文里说“已最优”。
- 模型验证：至少一个独立实现/逐件仿真/闭合式与级数对照。
- 灵敏度、临界点、至少两个算例：数据写 `project/results/*.json` 和 `solution.json`。
- 临界点必须给绝对参数值 + 单位 + 扫描域，不能把乘性倍数当参数值。
- 调试禁止删约束、缩规模、换更简单算法来“换过”；原文件修复最多 3 次。

## 5. 返工

- 读 `decision_logs/rework_brief.json`；只改 `change`，`keep` 不得重开，遵守 `forbidden`。
- `fresh_dossier`：先读 `failure_dossier.json`，写 `rework_plan.json`，过计划门再写代码；旧产物只作负证据。
- `resume`：只修 brief 的点；交接末尾写「相对返工单的交代」。

## 6. 自检（工具脚本暂留 `tools/checks/`，Phase 3 迁 `tools/`）

```powershell
.venv\Scripts\python.exe tools\checks\check_solution_json.py result_bundle/solution.json project/results --selfcheck
.venv\Scripts\python.exe tools\checks\check_modeling_artifacts.py <项目根> --scope modeling
```

ERROR 当场修；WARN 记录。然后调用 `pipeline_submit(stage="MODELING", role="solver", produced_by="solver")`。

## 7. 禁止

- 跳过最优性/模型验证/灵敏度。
- 出图、写 `result_bundle/figures/`。
- 写 `method_critique`、论文、`run_state.json`、`pipeline_state.json`。
- 把同题专有符号/数据写入 `tools/checks/` 或 skill references。
