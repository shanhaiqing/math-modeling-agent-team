# 题面覆盖事故复盘（2024B，2026-10-19）

## 发生了什么

- 赛题：2024 CUMCM B《生产过程中的决策问题》，题面共 **4 问**。
- Lead 只读了 `赛题/题面.md` 前 120 行（到问题2 和表1），写 brief 时只列了问题1、问题2。
- Solver 严格按 brief 执行，交付了 Q1/Q2，并在 `handoff_notes_1.md` 的「建模遗留项」里写明问题3/4 未做。
- Method 按完整题面核查，发现 `solution.json` 只有 Q1/Q2，判 `BLOCKED`，`recommend=rollback`。
- 机查 `check_solution_json.py` 是 **0 ERROR**：它只核契约字段和 Q1/Q2 内部一致性，不核“题面 4 问是否都覆盖”。

## 根因

**不是 Solver 漏做，是 Lead 的 brief 范围不完整。**

```text
Lead 读题不完整 → brief 只写 Q1/Q2 → Solver 按 brief 做 Q1/Q2
→ Method 按完整题面核查 → 发现 Q3/Q4 缺失 → BLOCKED
```

Solver 其实看到了题面有 4 问（handoff 里写了遗留项），但按“按 brief 执行”的纪律没有擅自扩大范围；缺少的是“brief 与题面不一致时必须上报 Lead”的规则。

## 修复（已写进 skills）

1. **`pipeline-protocol`（Lead）**：G0 必须读完题面全文，写 `decision_logs/problem_coverage.json`；brief 必须带 coverage；没列全不得进 MODELING。
2. **`solver-opt` / `solver-stats`**：开工前核对 coverage；缺失或覆盖数 < 题面问题数 → 报告 Lead，不开工；提交前逐问核对 `solution.json`，缺一问 = ERROR。
3. **`method-critic`**：覆盖门先于四问；缺任一 Q → `BLOCKED`，不进入天花板讨论。
4. **`system/team/team-blueprint.md`**：派活模板加 coverage 路径与核对步骤。

## coverage 文件形状

```json
{
  "run_id": "b-test-01",
  "source": "赛题/题面.md",
  "count": 4,
  "questions": [
    {"id": "Q1", "title": "抽样检测方案", "required_outputs": ["sample_size", "decision_rule", "result"]},
    {"id": "Q2", "title": "表1 六情形生产决策", "required_outputs": ["strategy", "profit", "sensitivity"]},
    {"id": "Q3", "title": "两道工序 8 零配件推广", "required_outputs": ["strategy", "profit", "sensitivity"]},
    {"id": "Q4", "title": "抽样次品率重做 Q2/Q3", "required_outputs": ["sampling_uncertainty", "strategy", "robustness"]}
  ]
}
```

## 后续可加机查（Phase 2B/2C）

- Kernel 产物加 `problem_coverage`，机查 `solution.json` 的键是否覆盖 coverage 的每个 Q。
- 这是“机器能查的规格”，不应只靠 agent 记忆；当前先用 skill 契约兜住。

## 当前状态

- 测试 run `b-test-01` 已 **交付（DELIVERED）**：覆盖契约在 local 返工中验证通过，Q3/Q4 补齐；最终 review 94/100 ACCEPT。
- 覆盖契约已补进 3 类 skill（Lead / Solver 两轨 / Method）和 Team blueprint。
- 2024B 全过程见 [`2024b-run.md`](2024b-run.md)。
