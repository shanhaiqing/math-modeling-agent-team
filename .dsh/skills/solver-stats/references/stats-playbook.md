# Stats 轨建模求解 Playbook

> 这是 `solver-stats` 的领域参考。角色流程以 `SKILL.md` 为准；完整旧版角色文本在 `legacy-solver-stats.md`；方法库在 `method-cards/` 与 `data-decision-tree.md`。

## 1. 先看数据，再定任务

1. 读 `赛题/题面.md` 与 `赛题/附件/`；禁止自行从 PDF 抽取题面。
2. 超过 1000 行不要全量读入；用 pandas 输出规模、字段类型、缺失、±3σ 异常、分布摘要和前后各 10 行，写入指纹的 `data_quality`。
3. 读 `data-decision-tree.md`、`method-cards/`、`data-conventions.md`、`paper-index.md`；方法卡可以否决。
4. 在 `modeling_plan.json` 写 `design_critique`、`data_feasibility`、`leakage_check`、`source_parameters`；有下游决策时写 `downstream_decision_kind`（`downstream_optimization=yes` 时不许填 `na`）。

## 2. 交付字段

- `result_bundle/solution.json`：每子问题必须有 `task_type`、`objective_or_goal`、`metrics`（含划分口径）、`model.selection`（至少两个候选 + 一个基线）、`validation`（含 `overfitting_check`）、`preprocessing`（含 `train_test_isolation`）、`data_lineage`、`sensitivity`、`monte_carlo`（不适用 null + 说明）。
- `result_bundle/feature_fingerprint.json`：按 stats 模板。
- `result_bundle/modeling_plan.json`、`术语表.json`、`project/` 求解脚本、`project/results/*.json`。
- `handoff_notes_1.md`（≤800 字；讨论项/遗留项分开）。

## 3. 验证红线

- 预处理、特征选择、调参、降维只在训练折内完成；全数据拟合后再划分 = 泄漏。
- 时序/分组数据禁止随机划分。
- 复杂模型必须和至少一个简单基线对比。
- 灵敏度至少一种数据扰动：特征扰动、bootstrap 或多个随机种子划分。
- 没有识别设计时不写因果效应；因果措辞按 `data-conventions.md`。
- 过拟合、泄漏检查、基线对比都要真跑，不能只在散文里声称。

## 4. 工具

- 监督学习可用 `data_modeling_template.py` 的 `split_data` / `preprocess_fit_transform`；时序主模型不要把该模板的监督骨架当主模型。
- 打包前：

```powershell
.venv\Scripts\python.exe .trae\code_templates\check_solution_json_stats.py result_bundle/solution.json project/results --selfcheck
.venv\Scripts\python.exe .trae\code_templates\check_leakage.py project
.venv\Scripts\python.exe .trae\code_templates\check_modeling_artifacts.py <项目根> --scope modeling
```

`check_leakage` 只报 WARN，不因此停；ERROR 当场修。不要用 opt 的 `check_solution_json.py` 验收本轨。

## 5. 返工

- 读 `rework_brief.json`；只改 `change`，遵守 `keep`/`forbidden`。
- `fresh_dossier`：先写 `rework_plan.json`，过计划门再写代码；旧产物只作负证据。
- `resume`：只修 brief 点；交接末尾写相对返工单的交代。

## 6. 禁止

- 跳过验证设计、过拟合自查、灵敏度。
- 在全数据上拟合预处理/调参后再划分。
- 出图、写 `result_bundle/figures/`。
- 写 `method_critique`、论文、`run_state.json`、`pipeline_state.json`。
- 把同题专有符号/数据写入 `.trae/` 或 skill references。
