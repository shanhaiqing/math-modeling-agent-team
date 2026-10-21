# Tabletop Tests · 8 个运行场景

> 用途：在写 Kernel 之前，用纸面轨迹验证状态机、门、契约、机查、预算、stale 是否自洽。
> 每个场景给出：初始条件 → 动作序列 → 预期状态 → 断言。Phase 1 的 Kernel 测试可直接把这些序列编码成 JSON。
> 状态名与 `framework.json.stages` 一致；转移以 `framework.json.transitions` 为准。

## 通用断言（每个场景都检查）

1. 每次状态变化都有一条 `events.jsonl` 记录；`run_state.stage` 与最后一事件一致。
2. 每个门决策都写入 `gate_decisions.jsonl`，含 `artifact_hashes`；`decided_by` 为 `human` 或 `auto`。
3. 每个阶段退出前，`checks` 中该阶段的检查全部有终态（pass/warn/fail/skipped），ERROR=0（允许 WARN 的除外）。
4. `check_pipeline_manifest` 在业务检查之后、`check_machine_checks` 之前执行。
5. 被批准过的 artifact hash 不变；变了则 gate 失效并进入对应 repair 路径。
6. 任何阶段不得超过 `limits`；超限进入 BLOCKED 或 G4。
7. `run_state.stale_stages` 与下游产物一致；stale 阶段不得被当作已完成。
8. `cost_report` 的阶段/角色条目覆盖所有实际执行的角色；token 不可用时为 null 并注明。
9. 所有 `resume` / `fresh_dossier` / `fresh_independent` 决定写入 `run_state.freshness_decisions[]`；`fresh_dossier` 必须有 `failure_dossier` + `rework_plan` + `regression_check_report`，缺一不得 submit。

---

## T1 · 干净 opt 路径（G1 自动放行，评审一次通过）

**初始**：`contest_profile=cumcm`，`problem_track=opt`，`profile=quality`，题面齐备。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Lead | `pipeline_start` 创建 run | INIT | run_state/events/gate_decisions |
| 2 | Lead | `pipeline_submit(INTAKE)` | INTAKE | 题面、ingest_report；intake 检查 pass |
| 3 | Human | G0 approve | MODELING | G0 记录；track=opt |
| 4 | Solver | 产出 bundle；`pipeline_submit(MODELING)` | MODELING → METHOD | modeling 检查 pass；contract/manifest 0 ERROR |
| 5 | Method | `pipeline_submit(METHOD)` | METHOD → METHOD_GATE | method_critique；verdict=PASS |
| 6 | Kernel | G1 auto：verdict=PASS 且无票 | FIGURES | G1 `decided_by=auto`，不等人 |
| 7 | Figures | `pipeline_submit(FIGURES)` | FIGURES → MODEL_REVIEW | ≥6 组 PDF+PNG；visual_qa 0 ERROR |
| 8 | Human | G2 approve | WRITING | G2 记录；figures/solution hashes |
| 9 | Writer | `pipeline_submit(WRITING)` | WRITING → DRAFT_REVIEW | paper.tex/pdf；compliance 0 ERROR |
| 10 | Human | G3 approve | REVIEW | G3 记录；paper hash |
| 11 | Reviewer | `pipeline_submit(REVIEW)` | REVIEW → COMPLIANCE | verdict=PASS，无 high |
| 12 | Kernel | G4 auto skip | COMPLIANCE | 不找人 |
| 13 | Kernel | `pipeline_submit(COMPLIANCE)` | COMPLIANCE → DELIVER | packaging 0 ERROR；manifest 0 ERROR |
| 14 | Human | G5 deliver | DELIVERED | MD5 记录；cost/run report |

**断言**：
- 人工交互 = 4 次（G0/G2/G3/G5）；G1/G4 自动，记录 `auto`。
- `cost_report` 中 solver/method/figures/writer/reviewer 均有条目；model=`deepseek-flash`，effort 按档位。
- `run_report` 中 `compliance_errors=0`、`verification_completeness=100%`、`high_severity_open=0`。

**变体**：`profile=balanced` 时，solver/method/reviewer 仍 max，Lead/Writer/Figures high；轨迹不变。

---

## T2 · stats + leakage WARN（WARN 不阻塞，reviewer 裁定）

**初始**：`problem_track=stats`，`profile=balanced`。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Lead | INTAKE submit；G0 approve | MODELING | track=stats |
| 2 | Solver | 产出 stats bundle；submit | MODELING | solution_stats 检查 pass；`check_leakage` WARN |
| 3 | Kernel | 建模门：ERROR=0，leakage WARN | METHOD | leakage_report 存在；不阻塞 |
| 4 | Method | verdict=PASS_WITH_NOTES，票=limitations_only，recommend=proceed | METHOD_GATE | 票 1 张 |
| 5 | Kernel | G1 auto（全部 limitations_only + proceed） | FIGURES | G1 `auto`；票写入模型评价 |
| 6 | Figures | submit | MODEL_REVIEW | 图检查 pass |
| 7 | Human | G2 approve | WRITING | G2 记录；票在包内回显 |
| 8 | Writer | 写作；submit | DRAFT_REVIEW | compliance pass |
| 9 | Human | G3 approve | REVIEW | — |
| 10 | Reviewer | 全文评审；leakage WARN 裁定；verdict=PASS | COMPLIANCE | review_scores 有 WARN 裁定行 |
| 11 | Kernel | G4 skip；compliance；G5 | DELIVERED | — |

**断言**：
- leakage WARN 出现在 G2 包与 review_scores；reviewer 必须给出裁定（接受/修复），不能忽略。
- stats 检查使用 `check_solution_json_stats.py`，不得用 opt 检查器。
- `check_leakage.py` 报告存在；即使 WARN 也需要文件。

**变体**：leakage WARN 若被 reviewer 升级为 high → REVIEW → FIX_R1；修复后复审仍走 stats 检查。

---

## T3 · METHOD BLOCKED → G1 回退 → fresh+dossier 返工 → 重跑 METHOD

**初始**：`problem_track=opt`，`profile=quality`。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Lead/Solver | 正常到 MODELING submit | METHOD | — |
| 2 | Method | verdict=BLOCKED；recommend=rollback；ticket 会改结论形态 | METHOD_GATE | method_critique.json |
| 3 | Human | G1 rollback | MODELING | G1 记录 |
| 4 | Kernel | 判定 `fresh_dossier`；写 `failure_dossier.json` + `rework_brief.json`（mode/return_to=MODELING）；标 stale；旧 code 放 attic | MODELING | dossier 含 failure_modes、rejected_signature、must_not_repeat、acceptance_tests、attic_paths |
| 5 | Solver（fresh） | 读 dossier + brief + attic；**先写 rework_plan，不动代码** | MODELING | plan 覆盖每个 failure_mode 的 countermeasure/verification/regression |
| 6 | Kernel | 计划门：发现 F1 未给 regression test，退回改计划；第 2 版通过（≤2 次） | MODELING | `modeling_rework_plan` check pass；`rework_plan.json` |
| 7 | Solver | 编码；submit | MODELING → METHOD（T55，return_to=METHOD） | regression_checks 跑通；report 存在；rework 计数 +1 |
| 8 | Kernel | `repeat_failure=false`；清除 stale 中 MODELING | METHOD | — |
| 9 | Method | 重跑；verdict=PASS | METHOD_GATE → FIGURES | 覆盖旧 critique |
| 10 | Kernel | G1 auto；继续 | FIGURES | — |

**断言**：
- 回退前旧 METHOD/FIGURES/WRITING/REVIEW 产物存在也不能被当作已完成；stale 标记必须生效。
- fresh solver **不 resume** 被否的 solver；它继承的是失败档案 + attic，不是旧对话。旧 code 只作负证据。
- 计划门在编码前执行；每个 failure_mode 必须有 countermeasure + verification + regression test；与 rejected_signature 结构性相似时须有新证据；计划修订 ≤2 次。
- 回归测试必须复现旧失败并证明已修；`regression_check_report.json` 不过不得 submit。
- T55 回到最早 stale 的下游；方法结构变了才回 METHOD，局部数值修复可回 FIGURES/MODEL_REVIEW。
- `modeling_rework_total` 计数 ≤3；同一 failure_mode 重复 → `repeat_failure=true` → G1/G4，不允许第三次 fresh 未经人批准。
- 重跑 METHOD 覆盖两份 critique，不得保留旧 verdict。

**变体**：G1 rollback 后用户改选 proceed → 记录 waiver_risk；METHOD 的 BLOCKED 仍进入 run_report。

### T3b · 局部返工走 resume（不重跑整轮 METHOD）

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Human | G2 return_modeling：子问 2 的目标值算错，模型/方法不变 | MODELING | G2 记录；Kernel 判定 `resume` |
| 2 | Kernel | 写 fix brief（keep/change/forbidden）；不写 failure_dossier；标 FIGURES/WRITING/REVIEW stale | MODELING | `freshness_decisions` mode=resume；同 solver child id |
| 3 | Solver | resume 同一 child；只改 change 范围内的数值/代码；submit | MODELING → FIGURES（T55，return_to=FIGURES） | 只跑受影响检查；不重跑 METHOD |
| 4 | Figures | 只重绘受影响的图；submit | FIGURES → MODEL_REVIEW | 图数值与 solution 一致 |
| 5 | Human | G2 approve | WRITING | G2 新 hash |

**断言**：
- 局部返工不建失败档案、不写 rework plan、不重跑整轮 METHOD；省下的正是 resume 的收益。
- 同一 solver child 续接；旧代码在上下文里，但 fix brief 限定 keep/change/forbidden。
- 只重跑受影响检查；若改动实际触及模型结构，Kernel 立即升级为 `fresh_dossier`，不得继续 resume。
- 下游 stale 按受影响范围重算；不能让旧图/旧论文继续沿用旧数值。

---

## T4 · G2 图面退回 → 重绘 → 批准；批准后 hash 失效

**初始**：`problem_track=opt`，已到 MODEL_REVIEW。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Human | G2 return_figures（图 3 轴缺单位；图 5 图型错） | FIGURES | G2 记录；图表清单追加退回反馈 |
| 2 | Figures | fresh specialist 读反馈；只改图面；submit | FIGURES → MODEL_REVIEW | 数值不变；visual_qa 0 ERROR；figure_returns +1 |
| 3 | Human | G2 approve | WRITING | G2 记录；figures hash |
| 4 | Figures | 事后擅自改图（模拟违规） | WRITING → MODEL_REVIEW | Kernel 检测 hash mismatch；gate stale；T53 |
| 5 | Human | 重新 G2 approve | WRITING | 新 hash；旧批准失效 |

**断言**：
- 图面退回不写 modeling brief；不退回 solver。
- 图重绘不得改 `solution.json` 数值；若改数值 → 退回 MODELING（BLOCKED）。
- G2 批准绑定 `figures_dir`/`figure_list`/`solution` hash；任一变化 → gate stale，T53 回 MODEL_REVIEW。
- `figure_returns` 上限 2；第 3 次不达标 → 人接受/停止。

**变体**：退回原因是"图 3 的数值与 solution 不一致" → 这不是图面问题，走数值路由回 Solver。

---

## T5 · 评审 R1/R2 残留 → G4 接受风险

**初始**：已到 REVIEW。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Reviewer | verdict=REJECT；2 个 high severity | REVIEW → FIX_R1 | review_report/scores |
| 2 | Kernel | 快照 paper/solution；生成 fix_points_round1；判定 R1=**resume**（局部表达/一致性修复） | FIX_R1 | snapshot + diff 锚；freshness_decisions |
| 3 | Writer | 逐条处置；2 fixed / 1 rejected；submit | FIX_R1 → RE_REVIEW_R1 | fix_round1.md；paper 重编译 |
| 4 | Reviewer（resume） | 全文复读；逐项重验；仍 1 high + 1 新 medium | RE_REVIEW_R1 → FIX_R2 | 更新报告；标注 round=1；不得假设"提过就已修" |
| 5 | Kernel | fix_failure_rate 计算；新 cross-section error → R2 reviewer=**fresh**；生成 fix_points_round2 | FIX_R2 | freshness_decisions mode=fresh |
| 6 | Writer | 修复；submit | FIX_R2 → RE_REVIEW_R2 | fix_round2.md |
| 7 | Reviewer（fresh） | 全文复读；上轮报告+fix log+diff 作核对清单；仍 1 high | RE_REVIEW_R2 → ADJUDICATION | round=2；r2 已用；独立评分，不抄上轮 |
| 8 | Human | G4 accept + waiver_risk | COMPLIANCE | G4 记录；残留项入 run_report |
| 9 | Kernel | compliance；G5 | DELIVERED | 交付带风险记录 |

**断言**：
- 修复轮次 ≤2；不得借退回重置轮次。
- R1 工单未全部执行/逐项记录理由 → 不得进 R2。
- R1 局部修复可 **resume** 同一 reviewer；它知道上轮问题，验证更准，但必须全文复读、逐项重验，禁止增量评审，禁止假设"我提过就已修"。
- R2 在 fix_failure_rate ≥30%、出现跨节新错、修复触及数值/模型时换 **fresh** reviewer；fresh 拿到上轮报告 + fix log + diff 作核对清单，但不拿 writer 对话与 `method_critique`，独立评分、不抄上轮分数。
- 所有 resume/fresh 决定写 `run_state.freshness_decisions[]`；不得由 reviewer 自行决定续接或重启。
- 复审必须全文通读，不能只读 diff；`fix_points_roundN.md` 只是锚。
- 修复涉及数值/移位 → 修复点所在小节全节数值重算。
- 图面缺陷 → Figures 重跑；writer 只改 caption/路径；根源数值错 → BLOCKED → Solver。
- G4 accept 必填 `waiver_risk`；残留 high 在 run_report 中可见。

**变体**：R1 后无 high → RE_REVIEW_R1 → COMPLIANCE（跳过 R2）；记录 `r2_skipped` 与理由。R1 的 high 是模型/数值根源问题 → 直接 fresh reviewer，不走 resume。

---

## T6 · 合规超页 → Writer 压缩 → 重跑 COMPLIANCE（不走 G3）

**初始**：已到 COMPLIANCE；正文 33 页（cumcm 上限 30）。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Kernel | `writing_compliance` ERROR：正文 33 > 30 | COMPLIANCE | latex_compliance_report ERROR |
| 2 | Kernel | 判定为 compliance repair；T46 | WRITING | repair_scope=compliance |
| 3 | Writer | 按压缩预案删冗余、不删验证；重编译；submit；T52 | WRITING → COMPLIANCE | paper 新 hash；compliance pass |
| 4 | Kernel | 重跑 compliance | COMPLIANCE | 页数 ≤30；ERROR=0 |
| 5 | Human | G5 deliver | DELIVERED | MD5 在最后改动后生成 |

**断言**：
- 合规修复不得删最优性验证/模型验证/灵敏度；删除验证 → 拒绝提交。
- compliance repair 不走 G3（除非改动涉及摘要/结构/建模叙事；Kernel 按 `repair_scope` 判断）。
- 若压缩改变了摘要或正文叙事 → 回 DRAFT_REVIEW（G3），不得直接重跑 compliance。
- MD5 生成后不得再改文件。

**变体**：页数 <10（cumcm 下限）→ 补内容，不得注水；补的是验证/解析段。

---

## T7 · Agent 崩溃/无产出 → 重试 ≤2 → BLOCKED → 人工恢复

**初始**：MODELING 进行中。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Solver | specialist 崩溃/超时，无 submit | MODELING | Kernel 记录 retry 1 |
| 2 | Lead | fresh specialist 重试（带失败信息） | MODELING | retry 2 |
| 3 | Solver | 仍失败 | MODELING → BLOCKED | retry 耗尽；run_state.blocked |
| 4 | Lead | 通知用户；不自行继续 | BLOCKED | blocked_history 记录 |
| 5 | Human | 选择 resume → MODELING | MODELING | T50；新 specialist；旧产物按 stale 处理 |
| 6 | Solver | 重新产出；submit | METHOD | 检查 pass |

**断言**：
- 重试 ≤2；每次重试是 fresh，不复用崩溃对话。
- BLOCKED 必须暂停等用户，不得自动跳过。
- 恢复时从当前阶段继续，不重跑已过门阶段；但未完成的阶段产物作废。
- 失败原因、重试次数、恢复选择写入 `blocked_history`。

**变体**：崩溃发生在 FIGURES/WRITING/REVIEW → 同样的重试/BLOCKED/恢复协议；不改变阶段上限。

---

## T8 · 预算超限（时间/token）→ 告警 → 压缩/暂停

**初始**：MODELING 已用 70% 时间盒。

| # | 角色 | 动作 | 预期状态 | 预期产物/检查 |
|---|---|---|---|---|
| 1 | Kernel | 70% 告警 | MODELING | `budget.warn` 事件 |
| 2 | Kernel | 90% 告警 + 压缩建议 | MODELING | 建议：候选 ≥2→1 + 备选说明 |
| 3 | Lead | 通知用户；选择压缩或继续 | MODELING | 决策记录 |
| 4 | Kernel | 100% 或 token hard cap | PAUSED/BLOCKED | 不自动继续；等用户 |
| 5 | Human | 延长预算/降档/停止 | MODELING/STOPPED | 记录 waiver/决策 |

**断言**：
- 70/90/100% 三档告警；预计超时 30% 必须给压缩方案。
- token soft=120% baseline、hard=150%；超 hard 暂停，不静默超支。
- 压缩只砍候选/算例/润色，不删验证项。
- 人工等待时间不计入阶段时间盒（或单独记 `human_wait_minutes`），避免把睡眠算成 agent 超时。

**变体**：tokenMeter 不可用 → 只用 wall/human 时间告警；cost_report token=null 并注明。

---

## 附 · 覆盖对照

| 场景 | 覆盖的门/路径 | 覆盖的失败模式 |
|---|---|---|
| T1 | G0/G2/G3/G5；G1/G4 自动 | 正常主链 |
| T2 | stats 轨；WARN 裁定 | 泄漏 WARN、票按局限 |
| T3 | G1 rollback；METHOD 重跑 | 方法错配、stale、返工上限 |
| T4 | G2 return_figures；hash 失效 | 图面退回、批准后改动 |
| T5 | R1/R2；G4 | 残留 high、修复失败率、全文复读 |
| T6 | COMPLIANCE repair；G5 | 页数、压缩、MD5 |
| T7 | 重试/BLOCKED/恢复 | agent 崩溃、无产出 |
| T8 | 预算告警/暂停 | 时间/token 超限 |

**通过标准**：8 个场景的预期状态序列与 `framework.json.transitions` 一致；无未定义状态/门/转移；每条断言都能在 Kernel 测试中自动检查（Phase 1）。
