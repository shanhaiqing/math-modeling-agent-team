# 编排器操作手册（主智能体一等实体）

> 本文件是主智能体（编排器）的显式定义：状态机、状态持久化、门控、机查执行、重试与回退。
> 流水线语义（团队/契约/红线/合规）以 `AGENTS.md` 为准，本文件不重复定义，仅定义**编排执行**。
> 对标校准与复盘不在本状态机，见仓库根目录 `进化工具包/`。

---

## 1. 角色定位

主智能体是流水线唯一编排者：题型与路径确认、subagent 调用、HG 门执行、状态持久化、机查执行、红线守卫、重试、回退、合规提醒。编排行为**以状态机为准**，不得以散文记忆替代状态记录。失败一律通知用户并暂停。

## 2. 状态机定义

```
HG0_INTAKE → MODELING → METHOD → FIGURES → HG1_GATE → WRITING → HG2_GATE
→ REVIEW_FIX(初审⇄R1⇄复审⇄R2) → HG3_GATE → COMPLIANCE → DELIVERED
```

### 附加态

| 态 | 触发 | 转移规则 |
|----|------|---------|
| BLOCKED | subagent 标记根源性错误 / 红线不过且不可现场修复 | 通知用户，确认后回退目标阶段 |
| USER_CLEANUP（用户裁决清理） | HG3 后用户下达清理指令 | 独立执行态，**不占 R1-R2 轮次**；执行内容、指令来源、结果写入 pipeline_state.json |
| RETREAT（HG 退回） | HG 门用户判退回 | 见第 6 节退回协议 |

## 3. pipeline_state.json 契约

**唯一状态载体**，每次流水线运行在项目根创建，逐阶段更新；模板见 `.trae/code_templates/pipeline_state_template.json`。字段：

| 字段 | 类型 | 更新时机 |
|------|------|---------|
| `system` | "B" | HG0 写入。引用 `.trae/` 文件前，本次必读只能是共用文件，或 `track_manifest.json` 里本轨列出的路径，或 handoff 点名的借卡文件 |
| `mode` | "competition" | HG0 写入（本仓库活流水线仅此值） |
| `contest_profile` | `cumcm` / `shuwei_zh` / `shuwei_en` | HG0 用户确认赛制剖面后写入；缺省、缺失、非法值一律视为 `cumcm` 并告知用户 |
| `problem_track` | `opt` / `stats` / null | HG0 用户确认后写入。缺失、null 或非法值不得进入 MODELING，不得当成 `opt`。用 `check_problem_track.py --state` 核验，退出码 1 即停 |
| `compile_mode` | external / null | WRITING 预检写入：xelatex 不可用 → `external`（编译降级模式）；本地可编译 → null |
| `project_root` | 绝对路径 | HG0 写入 |
| `current_stage` | 状态机态名 | 每次转移 |
| `passed_gates` | 数组（HG0/HG1/HG2/HG3 + 时间戳） | 过门时追加 |
| `fix_rounds_used` | `{R1: bool, R2: bool}` | 每轮修复后更新 |
| `stage_timestamps` | `{阶段名: {start, end}}` | 阶段起止（**耗时记录唯一载体**） |
| `machine_checks` | `{check名: {time, result, report_path}}` | 每次机查执行后追加 |
| `blocked_history` | 数组（触发者/原因/回退对象/结果/时间） | BLOCKED 每次触发 |
| `redline_results` | `{agent: {pass, missing[], time}}` | 红线核验后 |
| `subagent_ids` | `{subagent_type: agent_id}` | subagent 调用返回含 agent ID 时登记（供 resume 复用） |
| `rework_brief_active` | bool | 写入建模返工单时 `true`；该次 MODELING 红线通过后 `false`（brief 文件可留作审计）。缺省视为 `false` |
| `stale_stages` | 字符串数组 | 回退 MODELING 时写入已做过的下游阶段名（`method` / `figures` / `writing` / `review`）；该阶段重做完从数组去掉。缺省 `[]` |

禁止以"文件是否存在"反推状态——状态一律以本文件为准；本文件与实际产物冲突时，以实际产物为准并当场修正本文件。**例外**：`stale_stages` 非空时，对应阶段的磁盘产物（含旧 `paper.pdf` / `result_bundle/figures/`）视为作废，**不得**因这些文件存在而前推 `current_stage` 或视为已过门。

**断点接管协议（会话中断恢复）**：编排器新会话启动时，先检查 `{项目根}/pipeline_state.json` 是否存在——存在则读取 `current_stage`/`passed_gates`/`fix_rounds_used`/`machine_checks`/`rework_brief_active`/`stale_stages`/`contest_profile` 接管至对应状态继续编排，**禁止重跑已过门阶段**；状态与实际产物冲突时按上条当场修正后继续（`stale_stages` 例外仍适用）。`contest_profile` 缺失或不在 `cumcm` / `shuwei_zh` / `shuwei_en` 内 → 当场改为 `cumcm` 并告知用户。`problem_track` 缺失或不在 `opt` / `stats` 内 → 停在 HG0，不得进入 MODELING，不得改成 `opt`。`rework_brief_active` 为 true 时，不得把已有 `result_bundle/solution.json` 当作 MODELING 已完成。接管后仍须在 HG 门暂停等用户放行。

**subagent 上下文接力协议（resume 辅助机制）**：subagent 每次调用无久存对话状态，上下文接力遵循 `AGENTS.md` "handoff 契约"（自包含 prompt + 上游产出清单，一处定义），编排器不得假设同一 subagent 连续两次调用共享对话上下文。resume 仅作可选加速手段、不作主机制：条件触发——若某次 subagent 调用返回中回传 agent ID，则编排器须立即将其登记至 `pipeline_state.json` 的 `subagent_ids` 字段，供后续对该实例 `resume` 复用；未回传 ID 时禁止依赖 resume 续接上下文。

## 4. 阶段转换协议（机查收归编排器）

每次阶段转换前，编排器**亲自执行**（不得委托 subagent 自检代替）以下机查，报告写入规范路径并登记 `machine_checks`；ERROR 未清零不得推进：

| 转换 | 必跑机查 | 报告规范路径（项目根） |
|------|---------|----------------------|
| HG0 → MODELING | `convert_problem.py`（赛题 PDF / 说明类附件转写，xlsx/csv 不转）+ `check_workspace_hygiene.py` + **最后** `check_pipeline_manifest.py --stage intake` | `赛题/ingest_report.json` + `workspace_hygiene_report.json` + 更新 `manifest_check_report.json` |
| MODELING → 下一阶段 | 按 `track_manifest.json` 本轨的 `solution_check`（opt 为 `check_solution_json.py`，stats 为 `check_solution_json_stats.py`）+ `check_modeling_artifacts.py --scope modeling` + `check_code_hygiene.py project/` + `check_workspace_hygiene.py` + **最后** `check_pipeline_manifest.py --stage modeling`。**仅 stats** 另跑 `check_leakage.py project/ --report leakage_check_report.json`（WARN 不阻塞，但文件必须留下）。opt 不跑泄漏脚本，也不要求该报告 | `contract_check_report.json` + `modeling_artifacts_report.json` + `code_hygiene_report.json` + `workspace_hygiene_report.json` + `manifest_check_report.json`；stats 另有 `leakage_check_report.json` |
| METHOD → 下一阶段 | `check_workspace_hygiene.py` + **最后** `check_pipeline_manifest.py --stage method` | `workspace_hygiene_report.json` + 更新 `manifest_check_report.json` |
| FIGURES → 下一阶段 | `check_modeling_artifacts.py --scope figures`（P11-F 双格式配对 + P11-V visual_qa；`shuwei_en` 时 visual_qa 按 `pipeline_state.json` 禁图内 CJK）+ `check_workspace_hygiene.py` + **最后** `check_pipeline_manifest.py --stage figures` | `figures_artifacts_report.json` + `workspace_hygiene_report.json` + 更新 `manifest_check_report.json` |
| WRITING 启动前（预检） | `check_latex_env.py`（xelatex/关键宏包/中文字体，2026-08-B1；**任一 ERROR 报告用户，禁止 subagent 自行安装 TeX 发行版**；xelatex 不可用则进入编译降级模式——不阻塞流水线，`pipeline_state.json` 写入 `compile_mode=external`，编译移交用户外部执行；用户回传 `.aux`/`.log`/`.pdf`（三件缺一不可）后编排器补跑 `check_latex_compliance.py`）。**`contest_profile=shuwei_en` 加 `--contest-profile=shuwei_en`**（改检 pdflatex + `swmcmthesis`；中文字体缺失不升 ERROR） | `latex_env_report.json` |
| WRITING → 下一阶段 | `check_latex_compliance.py` + `check_tex_numbers.py`（WARN 级辅助，不阻塞）+ `check_abstract_guard.py audit paper.tex`（摘要篇幅/段落量化/关键词加粗，WARN 级辅助，2026-08-C2，终端输出即可；`verify` 仅在修复回路摘要定稿后按惯例 三.10 执行）+ `check_workspace_hygiene.py` + **最后** `check_pipeline_manifest.py --stage writing`。合规检查传 `--contest-year=`；**`shuwei_en` 时 compliance 与 abstract_guard 均加 `--contest-profile=shuwei_en`** | `latex_compliance_report.json` + `tex_number_check_report.json` + `workspace_hygiene_report.json` + 更新 `manifest_check_report.json` |
| REVIEW_FIX 每轮后 | `check_workspace_hygiene.py` + **最后** `check_pipeline_manifest.py --stage review` | `workspace_hygiene_report.json` + 更新 `manifest_check_report.json` |
| COMPLIANCE（打包） | `check_workspace_hygiene.py` + `package_support_materials.py`（只收代码+数据+图表，终扫未过不得交付，2026-08-B1；`compile_mode=external` 时须先过下方"编译降级专项条款"再打包） | `workspace_hygiene_report.json` + `packaging_report.json` |
| 任意共享文件落地后 | `check_prompt_budget.py` | 终端输出即可 |
| 惯例/共享规则落地后（`国赛公开惯例.md` 或引用惯例的文件改动时） | `check_convention_refs.py`（编号引用完整性 + 条款锚点目录对账） | 终端输出即可 |
| 绘图代码落地后（`visualization_style.py` / `figure-studio/`） | `check_viz_tests.py`（跑 4 个 `test_*` 回归测试，任一失败 ERROR） | 终端输出即可 |
| 方法卡片或求解器模板变更后 + MODELING 门（与 `check_modeling_artifacts.py` 同批） | `check_card_refs.py`（卡片→代码模板引用完整性：路径存在性、"自实现/待补"合法性） | 终端输出即可 |
| **每次阶段转换最后（manifest 之后）** | `check_machine_checks.py <项目根> --stage <阶段>`（机查执行证据链对账：虚报 PASS / 报告缺失 / 漏登记 / 陈旧报告；元机查，校验 machine_checks 登记与报告文件是否一致） | 终端输出即可（**默认不落盘、不入注册表**，避免与 manifest 循环依赖；需留证时 `--report machine_checks_audit_report.json`） |

**执行顺序铁律**：①`check_pipeline_manifest.py` 是齐备性门，会校验注册表内全部报告文件的存在性——**必须在同一转换内的其他机查全部落盘后最后执行**，否则会把尚未生成的报告误报为缺失 ERROR。②`check_machine_checks.py` 对账 machine_checks 登记，依赖 manifest 报告已落盘且已登记——**排在 manifest 之后**。故每次阶段转换的执行顺序恒为：各业务机查 → manifest → check_machine_checks。上表各行的脚本排列顺序即为执行顺序。

**编排器自证条款（堵"登记了≠执行了"）**：每次阶段转换推进前，须在向用户的状态更新中报告本次机查。全 0 ERROR 时一行带过（列出报告文件名即可）；仅当某份 `error_count≠0` 时逐份复述路径与 ERROR 数。`machine_checks` 由编排器自填、不可自证；未复述即推进，视同该机查未执行。WARN 不在此复述（裁定权惯例 五.1）。

WARN 的裁定权维持下游 agent 制度（惯例 五.1）不变——编排器只保证**机查被执行、报告存在、ERROR 清零**，不越权裁定 WARN。

**HG0 赛题转写协议**（题型判定前执行；脚本 `.trae/code_templates/convert_problem.py`）：

1. 确认项目根与 `contest_profile`（`cumcm` / `shuwei_zh` / `shuwei_en`；未选或非法 → `cumcm` 并告知用户）后写入 `pipeline_state.json`，再运行 `python .trae/code_templates/convert_problem.py --project-root <项目根>`（自动发现题面 PDF；用户也可 `--pdf` / `--attachments-dir` 指定）。
2. 产出 `{项目根}/赛题/题面.md`（按页原文转写，**禁止改写**）+ `赛题/ingest_report.json`；说明类 `.docx` 转 `赛题/附件/*.md`（条件）；PDF 嵌入图与疑似扫描页导出 `赛题/题面图/`（条件）。xlsx/csv 数据附件不转写。
3. `ingest_report.json` 的 `error_count` 未清零不得进入题型判定。编排器以 `赛题/题面.md` 做 HG0 题型判定。
4. 后续 MODELING / METHOD / FIGURES / WRITING / REVIEW 的强制喂料均含 `赛题/题面.md`（及存在的 `赛题/附件/`、`赛题/题面图/`）。**禁止**各 agent 自行 pymupdf 抽赛题 PDF。英文题同样只走本转写，不得因题面为英文而改抽 PDF。题面源图允许 Read。论文生成图：solver / writer / FIGURES / METHOD 禁止 Read；reviewer 核图文见 `AGENTS.md` 白名单。
5. 用户确认 `problem_track` 后写入 `pipeline_state.json`，运行 `python .trae/code_templates/check_problem_track.py --state {项目根}/pipeline_state.json`。退出码非 0 不得调用建模岗。过门：`check_pipeline_manifest.py --stage intake` ERROR 清零。将转写齐备、`contest_profile` 与 `problem_track` 纳入 HG0 审查卡后暂停。
6. 建模调用名取 `track_manifest.json` 本轨的 `solver_agent`。上游清单抄本轨的卡片目录、专项惯例、指纹模板和求解器名。返工仍调这一个名字。不要再调用 `modeling-solver`。

**METHOD 专项协议**（MODELING 红线通过后、FIGURES 前）：

1. **另起干净 Task**：禁止 inherit modeling-solver 上下文；禁止 resume Solver；禁止用编排器当前会话兼做本岗。模型钉强推理（默认平台 slug `kimi-k3-max`，用户可覆盖）；**禁止**用出图用的 GLM 兼做本岗。
2. **只喂**：`.trae/skills/method-studio/SKILL.md` + 本轨 `method_gate`（`gate_opt.md` 或 `gate_stats.md`，路径见 `track_manifest.json`）+ `.trae/code_templates/method_critique_template.md` + `赛题/题面.md` + 存在的 `赛题/附件/` + `result_bundle/feature_fingerprint.json` + `result_bundle/modeling_plan.json` + `result_bundle/solution.json` + `handoff_notes_1.md` + `project/` 下求解相关 `.py`。不喂图，不喂反思日志，不喂另一轨的 gate。本岗可自行 WebSearch 同题/同类论文。否决标准以本次喂入的闸门文件为准。
3. **产出**：`decision_logs/method_critique.md` + `decision_logs/method_critique.json`。不占 `handoff_notes` 编号。工作流按 method-studio：先闸门后天花板。
4. **并行**：与 solver/writer/reviewer/FIGURES 同级。不得与 MODELING / FIGURES / WRITING / REVIEW 并行。本岗不改 `project/`、不改 `solution.json`。
5. **过门**：`check_pipeline_manifest.py --stage method` ERROR 清零后，编排器必须向用户给出**推荐方案**（读 `method_critique.json` 的 `recommend`，不得省略、不得改判、不得只列选项）。简报顺序：verdict → 闸门一句 → 升级票摘要 → **【推荐】choice + reason** → 请用户确认或改选。分支——`BLOCKED`：推荐确认回退 MODELING，暂停等用户；用户否决回退须书面接受错配风险。`PASS` 且无票：推荐出图，一行简报后启动 FIGURES（用户当场反对则停）。`PASS_WITH_NOTES`：**必须暂停**。`recommend.choice=proceed` → 荐①放行出图（票写入模型评价）；`choice=rollback` → 荐②按 `ticket_index` 回退 MODELING。用户确认后按 §7「建模返工协议」写 brief 再调 solver（重求后重跑 METHOD 再出图）。用户可改选。禁止未给出推荐就出图或回退。
6. **重跑**：MODELING 回退重求后必须重跑本专项，覆盖两份产物。

**FIGURES 专项协议**（METHOD 红线通过后、HG1 前）：

1. **另起干净 Task**：禁止 inherit modeling-solver 上下文；禁止用编排器当前会话兼做绘图。模型钉 GLM（默认平台 slug `glm-5.2-high`，用户可覆盖）。
2. **只喂**：`.trae/skills/figure-studio/SKILL.md` + `.trae/code_templates/visualization_style.py` + `赛题/题面.md` + 存在的 `赛题/附件/` 与 `赛题/题面图/` + `project/results/*.json` + `result_bundle/solution.json` + `result_bundle/modeling_plan.json` + `handoff_notes_1.md`。**`contest_profile=shuwei_en` 另喂 `赛制/shuwei_en.md`**。工作流按 figure-studio 执行（设计卡→选型→绘制→`visual_qa` 程序自检→导出登记）。本岗可检索同题/同类论文图面作构图参考，不得把同题数据写入共享文件。
3. **禁止 Read 生成图**（PNG/PDF/WebP：`result_bundle/figures/`、`project/figures/`、论文编译页截图）。**允许** Read `赛题/题面图/`（题面源图）。程序自检 `visual_qa.py` 的 `audit_figure` / `scan` 除外；ERROR 未清零不得导出。感知层交 HG1 人工。
4. **产出**：`project/figures/` 与 `result_bundle/figures/`（PDF+PNG 双格式，≥6 组）+ `result_bundle/图表清单.md`。不占 `handoff_notes` 编号。
5. **并行**：与 solver/writer/reviewer/METHOD 同级。不得与 MODELING / METHOD / WRITING / REVIEW 并行。
6. **图面重绘**（修复回路或 HG1 图面退回）：同本协议重跑，覆盖双目录；数值禁止改动。HG1 图面退回反馈追加写入 `result_bundle/图表清单.md` 文末「HG1 退回反馈」节。

**复审修复点 diff 协议**（REVIEW_FIX，2026-09 批次 4）：初审调用前，编排器快照 `paper.tex` 与 `result_bundle/solution.json` 至 `decision_logs/_review_snapshots/r0/`；每轮 `fix_round{N}.md` 交付后、复审调用前，用 `git diff --no-index` 对比上一快照与当前版本（tex 节级 + JSON 字段级），汇总修复点清单写入 `decision_logs/fix_points_round{N}.md`，随复审调用 prompt 下发为修复点锚，随后更新快照。reviewer 全文通读义务不变（`AGENTS.md` 修复回路第 3 条），清单仅作验证锚点、不替代通读。

**编译降级专项条款**（条件触发：`compile_mode=external`，2026-09 批次 4；摘要 ≤1 页与正文页数为官方/红线硬约束，降级模式下由本条款兜底为交付前 ERROR 级门）：交付前编排器逐项确认——①最新 `paper.tex` 对应的用户回传件 `.aux`/`.log`/`.pdf` 三件齐备且同源（同一轮外部编译），缺件不得交付；②以回传件补跑 `check_latex_compliance.py`（**`shuwei_en` 加 `--contest-profile=shuwei_en`**），ERROR 清零；③若 `.aux` 缺失或无 `abstract:end` / `appendix:start` 锚点：摘要 ≤1 页与页数改为 PDF 人工实测——pymupdf 渲染摘要页与附录起始页 PNG 存 `decision_logs/page_check_evidence/`，实测结论写入 `decision_logs/manual_page_check.md`，无实测记录不得交付。**cumcm**：正文 = 摘要页之后、附录前，∈[10,30]，>30 不得交付。**`shuwei_en`**：Summary+目录+正文 = 附录起页−1，≤25（无 10 页下限），>25 不得交付；④补跑与实测完成后删除项目根 `.aux`/`.log` 等编译副产物（`paper.pdf` 保留），再执行工作区卫生与打包终扫。

## 5. 质量红线执行协议（状态机守卫）

subagent 返回后、以及 METHOD / FIGURES 专项完成后，编排器按 `AGENTS.md` 质量红线节逐项核验（产物存在性以 check_pipeline_manifest.py 结果为准），结果登记 `redline_results`（METHOD 用键 `method`，FIGURES 用键 `figures`）：

- 红线通过 → 更新 pipeline_state.json，推进状态机。刚完成 MODELING 且 `rework_brief_active` 为 true → 置 `false`。刚完成的阶段名若在 `stale_stages` 中，从数组去掉。
- 红线不过 → 通知用户并暂停。
- **红线不过而推进**是编排器违约。

## 6. HG 退回协议与重试

- **HG 退回**：退回对象 = 本阶段责任方。HG1 按缺陷分流：数值/模型 / 不接受 METHOD 错配或换方法结论 → modeling-solver（用户确认后按「建模返工协议」写 `rework_brief` 再调 solver；**不以** `handoff_notes_1.md`「HG退回反馈」为执行源；重求后必须重跑 METHOD 再出图）；图面 → 编排器按 FIGURES 专项重跑（反馈写入 `result_bundle/图表清单.md`「HG1 退回反馈」节；不写 modeling brief）。其余 HG 门退回对象 = 本阶段责任 subagent；反馈载体 = 在原 handoff_notes 追加"HG退回反馈"节（日期 + 退回理由 + 整改要求）。退回重跑后重新过同一 HG 门。**轮次衔接**：HG1/HG2 退回时修复回路尚未开始，修复回路轮次按初始状态处理；若退回发生在修复回路已消耗轮次之后，修复回路轮次计数不重置——**禁止借退回重置 R1/R2 上限**。
- **重试**：subagent 或 METHOD/FIGURES 专项 Task 崩溃或强制产出缺失 → 重试 ≤2 次（同一调用 prompt + 补充失败信息）；仍失败：通知用户并暂停。

## 7. BLOCKED 回退协议

- 回退对象判定：建模根源性错误 → MODELING；数据/数据理解错误 → MODELING；METHOD `verdict=BLOCKED` → MODELING；其余按标记内容归属。
- 回退对象为 MODELING 时：用户确认后按「建模返工协议」执行，禁止直接 @solver。
- **首次实际回退必须演练化记录**：回退执行后，将触发者、原因、回退对象、重跑结果、耗时写入 `blocked_history`——回退通道的存在性以"被走通过并记录"为验证标准。
- BLOCKED 必须暂停等用户确认后再回退，禁止自行跳过回退继续下游。

### 建模返工协议

凡回退对象为 MODELING（METHOD `choice=rollback` / `verdict=BLOCKED`、HG1 换方法或数值/模型退回、writer/reviewer BLOCKED、用户指令），用户确认后、调用 solver **前**必须按序：

1. 按 `.trae/code_templates/rework_brief_template.md` 与 `.json` 写入 `{项目根}/decision_logs/rework_brief.md` 与 `.json`。票面字段从 `method_critique.json` 或用户原文组装，**不得改判**。当前有效工单只此一份，再次回退覆盖。
2. `current_stage = MODELING`；从 `passed_gates` 去掉 HG1/HG2/HG3。
3. `stale_stages` 写入本轮之前已做过的下游阶段（`method` / `figures` / `writing` / `review` 中实际发生过的）。
4. `rework_brief_active = true`。
5. 调用 prompt 在 AGENTS.md 三件套之外加**第四块**（任务类型=返工；必读 brief；keep / change / forbidden / must_read **原样抄 JSON**，不得摘要改判）。上游产出清单必须列出 `decision_logs/rework_brief.md`。磁盘上有 brief 但清单未列，solver 不得自行当返工。
6. **默认另起干净 Task**，禁止 resume 被否方法；旧代码只通过 `must_read` 中的 `project/*.py` 等路径读取。

FIGURES 图面退回不走本协议。重求后必须重跑 METHOD 再出图，再停 HG1；不得因旧论文/图仍在磁盘而跳过。

## 8. 变更管理

本文件的修改须与 `AGENTS.md` 同步评审（两文件共同构成编排真相）；新增机查脚本须在 code_templates/ 注册并在本文件第 4 节表格登记执行时机。对话改进与规则落地见 `进化工具包/`。
