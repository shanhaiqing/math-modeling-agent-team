# Team Blueprint · Phase 2A

> 目标：把框架里的“角色”变成 DSH 能实际调用的团队：7 个 project-local skills + 一套 Lead 派活/交接模板。
> 本阶段**不新建 plugin/preset**，避免再次影响 live profile；Skills 在 `.dsh/skills/` 下，由 session 的 skill-filesystem 自动发现。
> Phase 2B 已在 2024B 完成（`DELIVERED`）；Phase 2C 已完成技能自包含（`SKILL.md + references/`，运行期不再引用 `.trae` 知识文件）。

## 1. 角色编制

| 角色 | DSH 形态 | 上下文 | 模型/effort | Skill | 写 | 禁写 |
|---|---|---|---|---|---|---|
| **Lead** | 当前 session | 持久 | flash/high（quality 可 max） | `pipeline-protocol` | gate packet / 派活 prompt | 专业产出、`run_state.json` |
| **Solver** | `subagent` 一次性 | fresh；局部返工 resume | flash/max | `solver-opt` / `solver-stats` | `project/**`、`result_bundle/**`、`handoff_notes_1`、`rework_plan.json` | 论文、图、`method_critique`、state |
| **Method** | `subagent` 一次性 | fresh，不继承 solver | flash/max | `method-critic` | `method_critique.*` | `project/**`、solution、论文、图、state |
| **Figures** | `subagent` 一次性 | fresh | flash/high | `figure-studio` | `result_bundle/figures/**`、`图表清单.md`、`project/figures/**` | solution 数值、论文、state |
| **Writer** | `spawn_teammate` 持久 | 初稿 fresh；R1/R2 续接 | 继承 Lead（high） | `paper-writer` | `paper.tex/pdf`、`abstract_candidates`、`handoff_notes_2`、`fix_round*` | 代码、solution、图、state |
| **Reviewer** | `subagent` 一次性 | fresh；R1 局部 resume；R2 高失败率 fresh | flash/max | `independent-reviewer` | `review_report.json`、`review_scores.md`、`handoff_notes_3` | 论文、图、solution、state |

**为什么这样分**：Method/Reviewer 需要独立，Figures 需要干净上下文，Solver 返工默认 fresh 避免锚定；Writer 需要 R1/R2 续接，所以用持久 teammate。`spawn_teammate` 没有模型参数，持久成员会继承 Lead 的 model/effort，因此 Lead 的 effort 要按档位设置（balanced=high；quality=max）。

## 2. Lead 的标准动作

```text
pipeline_status(project_root, view="brief")
  ↓
若是新 run：读完题面全文，写 decision_logs/problem_coverage.json（Q1..Qn）
  ↓
若需要派活：pipeline_freshness(role=..., trigger=..., scope=...)  ← 先定 resume/fresh
  ↓
按模板拼 brief（必须带 coverage 路径）→ subagent(...) / spawn_teammate(...)
  ↓
角色完成后 pipeline_status 看阶段/检查
  ↓
到门：pipeline_status(view="gate") → present/ask_user_question → pipeline_gate
```

**禁止**：Lead 自己写 solution/paper/figure/method_critique；禁止跳过 `pipeline_freshness` 直接决定续接/重启。

## 2.5 题面覆盖契约（G0 硬前置）

- Lead 必须读完 `赛题/题面.md` 全文，列出全部子问，写 `decision_logs/problem_coverage.json`：
  ```json
  {
    "run_id": "<run_id>",
    "source": "赛题/题面.md",
    "count": 4,
    "questions": [
      {"id": "Q1", "title": "...", "required_outputs": ["..."]}
    ]
  }
  ```
- 给 Solver/Method 的 brief 必须带 coverage 路径或全表；**coverage 没列全，不得进 MODELING**。
- Solver 开工前核对 coverage；不一致 → 报告 Lead，不擅自缩小/扩大范围。
- Method 覆盖门先于四问；solution 缺任一 Q → `BLOCKED`。
- 2024B 教训：Lead 只读题面前两问就派活，Solver 按 brief 做 Q1/Q2，Method 按 4 问核查才抓住；机查只核契约字段，不核题面覆盖。

## 3. 派活模板

### 3.1 Solver（subagent，fresh）

```text
description: "MODELING <run_id>"
prompt:
  你是本 run 的 Solver（<opt|stats>）。项目根：<abs root>。
  第一步：load skill `<solver-opt|solver-stats>`，读 `decision_logs/problem_coverage.json` 和 `赛题/题面.md` 全文。
  若 coverage 缺失，或 brief 覆盖的子问数 < 题面问题数 → 立即报告 Lead，不开工。
  工作范围 = coverage 的全部子问，不是 brief 的前几问。
  当前阶段：MODELING。freshness=<fresh|fresh_dossier|resume>。
  <若 fresh_dossier：先读 decision_logs/failure_dossier.json；先写 decision_logs/rework_plan.json，等计划门通过再写代码。>
  <若 resume：只改 rework_brief.change；keep 不动。>
  交付：<按 skill 的交付路径>。
  完成后运行自检，再调用 pipeline_submit(stage="MODELING", role="solver", produced_by="solver")。
  不要写 run_state.json / pipeline_state.json；不要出图；不要写 method_critique。
provider: deepseek-official
model: deepseek-flash
reasoning_effort: max
```

`subagent` 返回 child id；立刻用 `pipeline_freshness(..., child_id=...)` 登记，供后续 resume。

### 3.2 Method（subagent，fresh）

```text
load skill `method-critic`；项目根：<abs root>；只读题面/计划/结果/代码，不读论文。
先跑覆盖门：读 decision_logs/problem_coverage.json，solution 缺任一 Q → BLOCKED，不进入天花板。
读本轨 gate 文件；先闸门后天花板；写 method_critique.md/json；调用
pipeline_submit(stage="METHOD", role="method", produced_by="method")。
provider: deepseek-official
model: deepseek-flash
reasoning_effort: max
```

### 3.3 Figures（subagent，fresh）

```text
load skill `figure-studio`；项目根：<abs root>；先设计卡再画图；
读 solution/modeling_plan/results；不读论文；程序自检 visual_qa；
写 result_bundle/figures/ + 图表清单.md；调用
pipeline_submit(stage="FIGURES", role="figures", produced_by="figures")。
provider: deepseek-official
model: deepseek-flash
reasoning_effort: high
```

### 3.4 Writer（spawn_teammate，持久）

```text
name: writer-<run_id>        # 不要在多个 run 里复用同一个名字；Team 名字永久
description: "论文写作与 R1/R2 修复"
prompt:
  你是本 run 的 Writer。项目根：<abs root>。
  第一步：load skill `paper-writer`，读 result_bundle/图表清单/method_critique/handoff_notes_1。
  当前阶段：WRITING（或 FIX_R1/FIX_R2）。写 paper.tex/pdf + abstract_candidates + handoff_notes_2；
  修复轮读 review_report + fix_points + fix_round；图面问题交 Lead 转 Figures，不重绘。
  完成后调用 pipeline_submit(stage="WRITING|FIX_R1|FIX_R2", role="writer", produced_by="writer")。
context: fresh
```

Writer 持久成员继承 Lead 的 model/effort；R1/R2 用 `send_message` 续接，cold resume 也走同一 teammate。

### 3.5 Reviewer（subagent，fresh）

```text
load skill `independent-reviewer`；项目根：<abs root>；全文通读；
五维 + 本轨 12 项 + 红队；不读 method_critique、不读 writer 对话；
写 review_report/scores/handoff_notes_3；调用
pipeline_submit(stage="REVIEW|RE_REVIEW_R1|RE_REVIEW_R2", role="reviewer", produced_by="reviewer")。
provider: deepseek-official
model: deepseek-flash
reasoning_effort: max
```

R1 局部修复可 resume 同一 reviewer；R2 在 failure_rate ≥30% / 模型数值变动 / 跨节新错时换 fresh。

## 4. 门包与人工决策

1. `pipeline_status(view="gate")` 取门包字段。
2. 用 `present` 展示需要人看的文件（G2 看 6 张 PNG；G3 看 PDF；G5 看文件+MD5）。
3. `ask_user_question` 问：批准 / 退回建模 / 退回图 / 停止；退回时问原因类别。
4. 人回答后，把原话/选项写进 `pipeline_gate(gate, decision, reason, scope, root_cause)`；不得替人决定。
5. 退回后 Kernel 写 `rework_brief` / `failure_dossier`；Lead 只转述。

## 5. 失败与降级

| 情况 | 处理 |
|---|---|
| `subagent` 不可用 | 改用 `spawn_teammate`（统一继承 Lead 模型）或 `workflow.agent()` |
| Writer teammate 不可用 | 用 `subagent` + `paper-writer` skill；R1/R2 用 `send_message` 续接 |
| Solver 上下文丢失 | `pipeline_freshness(trigger="context_lost", context_lost=true)` → `fresh_dossier` |
| 同一 failure_mode 重复 | 升级 G1/G4；不允许第三次 fresh 未经人批准 |
| 插件工具不可用 | CLI 兜底：`tools/pipeline_kernel.py` |

## 6. Phase 2A 验收

- [x] 7 个 skill 出现在 DSH skill catalog：`pipeline-protocol`、`solver-opt`、`solver-stats`、`method-critic`、`figure-studio`、`paper-writer`、`independent-reviewer`。
- [x] Team 编制与派活模板写入本文件。
- [x] 不新建 plugin/preset，不改 live profile 的插件源码。
- [x] 题面覆盖契约写入 `pipeline-protocol` / `solver-opt` / `solver-stats` / `method-critic` + 本 blueprint（2024B 复盘）。
- [x] Phase 2B：用 2024B 跑真实链路，验证技能加载、brief 交接、`pipeline_submit/gate` 顺序；run `b-test-01` 已 `DELIVERED`（review 94/100 ACCEPT；见 `system/lessons/2024b-run.md`）。
