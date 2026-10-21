# G1 · 方法学决策门（METHOD 后，例外触发）

> 类型：条件触发 · 人工 · 10 分钟
> 记录：`gate_decisions.jsonl`，`gate_id=G1`

## 触发规则

只在以下情况找人：

- `verdict=BLOCKED`
- `recommend.choice=rollback`
- `tickets` 中存在 `action=optional` 且推荐回退

**自动放行**（不问人，记录 `decided_by=auto`）：

- `verdict=PASS` 且无票；或
- `verdict=PASS_WITH_NOTES` 且全部票为 `limitations_only`、`recommend.choice=proceed`。

自动放行的决定会在 G2 决策包里回显；人可以在 G2 反悔。

## 决策包

| 区块 | 内容 |
|---|---|
| verdict | `PASS` / `PASS_WITH_NOTES` / `BLOCKED` |
| 闸门 | 四条闸门各一句结论 + 证据位置 |
| 票 | ≤2 张：级别 / 替代方法 / 结构理由 / 是否改结论形态 / 重做代价 / action |
| 推荐 | 批评岗原样给出的 `choice` + `ticket_index` + `reason`；Lead 不得改判 |
| 成本 | 回退预计耗时 / token |
| 建议 | 放行 / 按票回退 / 停止 |

## 选项与去向

| 选项 | 去向 | 说明 |
|---|---|---|
| `proceed` | FIGURES | 无票或票按局限写入模型评价 |
| `rollback` | MODELING | 内核写 `decision_logs/rework_brief.{md,json}`；新 solver；重跑 METHOD |
| `stop` | STOPPED | 记录原因 |

## 退回单（内核写，不是 Lead 写）

`rework_brief.json` 必须含：`trigger`、`source_gate`、`ticket_index`、`keep`、`change`、`forbidden`、`must_read`、`return_scope`。新 solver 只改 `change`，不得把 `keep` 当新题重开。

## 禁止

- 未给推荐就出图或回退。
- 把 `BLOCKED` 稀释成建议。
- 用 `PASS_WITH_NOTES` 处理错配或会改结论形态的问题。
- Lead 改判批评岗的 `recommend`。
