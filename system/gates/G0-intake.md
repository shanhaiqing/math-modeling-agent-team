# G0 · 入口决策门（INTAKE）

> 类型：必过 · 人工 · 15 分钟
> 记录：`gate_decisions.jsonl`，`gate_id=G0`

## 目的

在进入 MODELING 之前，把会决定整条路径的四件事定下来：项目根、赛制、题型轨、题面齐备性。**题型轨没有默认值**；缺失或非法不得进入 MODELING。

## 决策包（内核生成）

| 区块 | 内容 | 来源 |
|---|---|---|
| 状态 | run_id / 项目根 / 当前阶段 / 已用时 | `pipeline_status` |
| 赛制 | `cumcm` / `shuwei_zh` / `shuwei_en` + 一句话依据 | 题面 + 用户选择 |
| 题型轨 | `opt` / `stats` + 判定依据；混合题只选一条主干 | `feature_fingerprint` 前置判定 |
| 题面 | `赛题/题面.md` 字数、页数、公式/表抽查结果；附件清单 | `ingest_report` |
| 运行档位 | `quality` / `balanced` / `economy` + 推荐 | 框架 §5.3 |
| 时间预算 | 72h 剩余、人工可用时段 | 用户输入 |
| 模型预检 | `deepseek-flash` + 所需 effort 是否可用 | 路由预检 |
| 风险 | ≤3 条：题面缺口、数据异常、环境风险 | 内核摘要 |
| 建议 | 批准 / 修正 / 停止 + 一句理由 | 内核 |

## 选项与去向

| 选项 | 去向 | 说明 |
|---|---|---|
| `approve` | MODELING | 前提：题面齐备、track 合法、模型可用 |
| `fix` | INTAKE | 修正项目根/赛制/题面/档位；最多 2 次 |
| `stop` | STOPPED | 记录原因 |

## 决策前机查

- `convert_problem.py` 产出 `赛题/题面.md`（≥200 字）与 `ingest_report.json`。
- `check_problem_track.py --state` 退出码 0。
- `check_workspace_hygiene.py` 无 ERROR。
- `check_pipeline_manifest.py --stage intake` 无 ERROR。

## 人工要看的只有

1. 题型轨是不是对？（错轨的代价最大）
2. 题面有没有漏页、公式乱码、附件缺失？
3. 赛制与运行档位是否认可？
4. 人工可用时段是否写对？

## 记录字段

`gate_id, run_id, stage, decision, reason, return_target, return_scope, artifact_hashes, decided_by, decided_at, timebox_met, recommendation, waiver_risk`

## 禁止

- 用默认 `opt` 兜底。
- 在题面不齐备时放行。
- 把 G0 当成"看一眼"；四项必须逐项确认。
