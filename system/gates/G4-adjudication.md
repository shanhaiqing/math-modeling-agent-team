# G4 · 残留问题裁决（ADJUDICATION，例外触发）

> 类型：条件触发 · 人工 · 20 分钟
> 记录：`gate_decisions.jsonl`，`gate_id=G4`

## 触发规则

- R2 复审后仍有 high severity
- 合规检查需要豁免
- 用户主动要求裁决

**自动跳过**：reviewer `verdict=PASS` 且无 high severity、合规无豁免 → 直接 COMPLIANCE。

## 决策包

| 区块 | 内容 |
|---|---|
| 状态 | 当前阶段、已用轮次、剩余时间 |
| 残留问题 | 每条：严重级别 / 位置 / 证据 / 为什么还没修 |
| 修复历史 | R1/R2 修了什么、失败率、是否引入新错 |
| 反驳记录 | 被 reviewer 驳回或 writer 反驳的项 + 证据 |
| 风险 | 接受后最坏会怎样；是否影响评奖资格 |
| 建议 | 接受风险 / 退回建模 / 退回写作 / 停止 |

## 选项与去向

| 选项 | 去向 | 说明 |
|---|---|---|
| `accept` | COMPLIANCE | 必须写 `waiver_risk`；接受项进入 run_report |
| `return_modeling` | MODELING | 根源性数值/模型问题；内核写 rework brief |
| `return_writing` | WRITING | 表达/一致性/遗漏；最后一轮 |
| `stop` | STOPPED | 记录原因 |

## 人工要判断的只有

1. 残留问题是否影响结论可信度或评奖资格？
2. 修复是否引入了更大的新错？
3. 接受风险是否值得？有没有时间再修？
4. 是否需要回退建模而不是继续写作？

## 禁止

- 无记录地接受 high severity。
- 用"时间不够"作为唯一理由，不写风险评估。
- 超过 2 轮修复后继续无限返工；G4 是终点裁决。
