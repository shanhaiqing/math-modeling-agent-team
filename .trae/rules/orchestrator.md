# 编排器操作手册（主智能体一等实体）

> 本文件是主智能体（编排器）的显式定义：状态机、状态持久化、门控、机查执行、重试与回退。
> 流水线语义（模式/团队/契约/红线/合规）以 `AGENTS.md` 为准，本文件不重复定义，仅定义**编排执行**。

---

## 1. 角色定位

主智能体是流水线唯一编排者：模式确认、subagent 调用、HG 门执行、状态持久化、机查执行、红线守卫、重试、回退、复盘组织、审批汇总、合规提醒。编排行为**以状态机为准**，不得以散文记忆替代状态记录。

## 2. 状态机定义

### 比赛模式

```
HG0_INTAKE → MODELING → HG1_GATE → WRITING → HG2_GATE
→ REVIEW_FIX(初审⇄R1⇄复审⇄R2) → HG3_GATE → COMPLIANCE → DELIVERED
```

### 训练模式

```
HG0_INTAKE → MODELING → WRITING → REVIEW_FIX(初审⇄R1⇄复审⇄R2)
→ CALIBRATION → RETRO_PARALLEL → APPROVAL → DONE
```

### 附加态（两种模式通用）

| 态 | 触发 | 转移规则 |
|----|------|---------|
| BLOCKED | subagent 标记根源性错误 / 红线不过且不可现场修复 | 比赛模式 → 用户确认后回退目标阶段；训练模式 → 记录 blocked_history 后继续下一阶段 |
| USER_CLEANUP（用户裁决清理） | HG3 或终点审批后用户下达清理指令 | 独立执行态，**不占 R1-R3 轮次**；执行内容、指令来源、结果写入 pipeline_state.json |
| RETREAT（HG 退回） | HG 门用户判退回 | 见第 6 节退回协议 |

## 3. pipeline_state.json 契约

**唯一状态载体**，每次流水线运行在项目根创建，逐阶段更新；模板见 `.trae/code_templates/pipeline_state_template.json`。字段：

| 字段 | 类型 | 更新时机 |
|------|------|---------|
| `system` | "B"（C 系统为"C"） | HG0 写入；**防混同锚点**——编排器引用任何 `.trae/` 镜像文件（惯例/机查/agent 文件）前，校验本字段与项目根路径所属系统一致：项目根在 B 系统目录下则一切引用 B 侧文件、借用 C 侧资产走 C4③ 白名单，反之亦然（2026-08-C5） |
| `mode` | competition / training | HG0 写入 |
| `compile_mode` | external / null | WRITING 预检写入：xelatex 不可用 → `external`（编译降级模式）；本地可编译 → null |
| `project_root` | 绝对路径 | HG0 写入 |
| `reference_paper_dir` | 绝对路径 / null | HG0 写入（训练模式） |
| `current_stage` | 状态机态名 | 每次转移 |
| `passed_gates` | 数组（HG0/HG1/HG2/HG3 + 时间戳） | 过门时追加 |
| `fix_rounds_used` | `{R1: bool, R2: bool, R3: bool}` | 每轮修复后更新 |
| `stage_timestamps` | `{阶段名: {start, end}}` | 阶段起止（**耗时记录唯一载体**） |
| `machine_checks` | `{check名: {time, result, report_path}}` | 每次机查执行后追加 |
| `isolation_signatures` | 数组（特征串，≥3 条） | 首次泄漏审计前从隔离区提取物现场提取后登记（签名规程见 §8 第 4 步）；**顶层字段，不并入 machine_checks 条目结构** |
| `blocked_history` | 数组（触发者/原因/回退对象/结果/时间） | BLOCKED 每次触发 |
| `redline_results` | `{agent: {pass, missing[], time}}` | 红线核验后 |
| `subagent_ids` | `{subagent_type: agent_id}` | subagent 调用返回含 agent ID 时登记（供 resume 复用） |

禁止以"文件是否存在"反推状态——状态一律以本文件为准；本文件与实际产物冲突时，以实际产物为准并当场修正本文件。

**断点接管协议（会话中断恢复）**：编排器新会话启动时，先检查 `{项目根}/pipeline_state.json` 是否存在——存在则读取 `current_stage`/`passed_gates`/`fix_rounds_used`/`machine_checks` 接管至对应状态继续编排，**禁止重跑已过门阶段**；状态与实际产物冲突时按上条当场修正后继续。训练模式下接管继续属全自动推进，不视为中途暂停。

**subagent 上下文接力协议（resume 辅助机制）**：subagent 每次调用无久存对话状态，上下文接力遵循 `AGENTS.md` "handoff 契约"（自包含 prompt + 上游产出清单，一处定义），编排器不得假设同一 subagent 连续两次调用共享对话上下文。resume 仅作可选加速手段、不作主机制：条件触发——若某次 subagent 调用返回中回传 agent ID，则编排器须立即将其登记至 `pipeline_state.json` 的 `subagent_ids` 字段，供后续对该实例 `resume` 复用；未回传 ID 时禁止依赖 resume 续接上下文。

## 4. 阶段转换协议（机查收归编排器）

每次阶段转换前，编排器**亲自执行**（不得委托 subagent 自检代替）以下机查，报告写入规范路径并登记 `machine_checks`；ERROR 未清零不得推进：

| 转换 | 必跑机查 | 报告规范路径（项目根） |
|------|---------|----------------------|
| MODELING → 下一阶段 | `check_solution_json.py` + `check_modeling_artifacts.py`（图表双格式配对/绝对路径/商业求解器，2026-08-B8）+ `check_code_hygiene.py project/`（交付代码注释卫生，2026-08-B1）+ `check_workspace_hygiene.py`（工作区卫生，本行内先于 manifest 执行）+ **最后** `check_pipeline_manifest.py --stage modeling`（齐备性门，须在本阶段其他机查报告全部落盘后执行，否则会误报缺失） | `contract_check_report.json` + `modeling_artifacts_report.json` + `code_hygiene_report.json` + `workspace_hygiene_report.json` + `manifest_check_report.json` |
| WRITING 启动前（预检） | `check_latex_env.py`（xelatex/关键宏包/中文字体，2026-08-B1；**任一 ERROR 报告用户，禁止 subagent 自行安装 TeX 发行版**；xelatex 不可用则进入编译降级模式——不阻塞流水线，`pipeline_state.json` 写入 `compile_mode=external`，编译移交用户外部执行；用户回传 `.aux`/`.log`/`.pdf`（三件缺一不可）后编排器补跑 `check_latex_compliance.py`） | `latex_env_report.json` |
| WRITING → 下一阶段 | `check_latex_compliance.py` + `check_tex_numbers.py`（WARN 级辅助，不阻塞）+ `check_abstract_guard.py audit paper.tex`（摘要篇幅/段落量化/关键词加粗，WARN 级辅助，2026-08-C2，终端输出即可；`verify` 仅在修复回路摘要定稿后按惯例 三.10 执行）+ `check_pipeline_manifest.py --stage writing` | `latex_compliance_report.json` + `tex_number_check_report.json` + 更新 `manifest_check_report.json` |
| REVIEW_FIX 每轮后 | `check_pipeline_manifest.py --stage review` | 更新 `manifest_check_report.json` |
| CALIBRATION → RETRO | `check_pipeline_manifest.py --stage calibration` + `check_isolation.py --signature ...`（泄漏审计，签名规程见 §8 第 4 步） | 更新 `manifest_check_report.json` + `isolation_check_report.json` |
| COMPLIANCE（打包） | `package_support_materials.py`（只收代码+数据+图表，终扫未过不得交付，2026-08-B1；`compile_mode=external` 时须先过下方"编译降级专项条款"再打包） | `packaging_report.json` |
| 任意阶段转换（工作区卫生） | `check_workspace_hygiene.py`（扫描项目根设计外垃圾，2026-08-B2） | `workspace_hygiene_report.json` |
| 任意共享文件落地后 | `check_prompt_budget.py` | 终端输出即可 |
| 惯例/共享规则落地后（`国赛公开惯例.md` 或引用惯例的文件改动时） | `check_convention_refs.py`（编号引用完整性 + 条款锚点目录对账） | 终端输出即可 |
| 绘图代码落地后（`visualization_style.py` / `figure-studio/`） | `check_viz_tests.py`（跑 4 个 `test_*` 回归测试，任一失败 ERROR） | 终端输出即可 |
| 方法卡片或求解器模板变更后 + MODELING 门（与 `check_modeling_artifacts.py` 同批） | `check_card_refs.py`（卡片→代码模板引用完整性：路径存在性、"自实现/待补"合法性） | 终端输出即可 |
| **每次阶段转换最后（manifest 之后）** | `check_machine_checks.py <项目根> --stage <阶段> --mode <模式>`（机查执行证据链对账：虚报 PASS / 报告缺失 / 漏登记 / 陈旧报告；元机查，校验 machine_checks 登记与报告文件是否一致） | 终端输出即可（**默认不落盘、不入注册表**，避免与 manifest 循环依赖；需留证时 `--report machine_checks_audit_report.json`） |
| **subagent 交付反思日志后**（MODELING 门核验 s1/s2/s3、WRITING 门核验 s4） | `check_reflection.py <项目根>`（反思日志反敷衍：套话密度 / 全 ✓ 无警示 / 空依据 / 依据过短 / 红队节空洞 / 篇幅异常六类特征） | 终端输出即可（**WARN 级不阻塞**——只识别敷衍的形式特征，裁定权按惯例 五.1 归 reviewer；需留证时 `--report decision_logs/reflection_check_report.json`） |

**执行顺序铁律**：①`check_pipeline_manifest.py` 是齐备性门，会校验注册表内全部报告文件的存在性——**必须在同一转换内的其他机查全部落盘后最后执行**，否则会把尚未生成的报告误报为缺失 ERROR。②`check_machine_checks.py` 对账 machine_checks 登记，依赖 manifest 报告已落盘且已登记——**排在 manifest 之后**。故每次阶段转换的执行顺序恒为：各业务机查 → manifest → check_machine_checks。上表各行的脚本排列顺序即为执行顺序。

**编排器自证条款（堵"登记了≠执行了"）**：每次阶段转换推进前，编排器须在阶段转换声明（向用户的状态更新 / 下游调用 prompt）中**复述本次每个机查报告的文件路径 + 报告内 error_count 数值**（如"contract_check_report.json: 0 ERROR / 2 WARN"）。`machine_checks` 由编排器自填、不可自证；复述使其对用户与 `check_machine_checks.py` 双向可见，虚报会在复述与报告实际值对账时暴露。未复述即推进，视同该机查未执行。

WARN 的裁定权维持下游 agent 制度（惯例 五.1）不变——编排器只保证**机查被执行、报告存在、ERROR 清零**，不越权裁定 WARN。

**复审修复点 diff 协议**（REVIEW_FIX，2026-09 批次 4）：初审调用前，编排器快照 `paper.tex` 与 `result_bundle/solution.json` 至 `decision_logs/_review_snapshots/r0/`；每轮 `fix_round{N}.md` 交付后、复审调用前，用 `git diff --no-index` 对比上一快照与当前版本（tex 节级 + JSON 字段级），汇总修复点清单写入 `decision_logs/fix_points_round{N}.md`，随复审调用 prompt 下发为修复点锚，随后更新快照。reviewer 全文通读义务不变（`AGENTS.md` 修复回路第 3 条），清单仅作验证锚点、不替代通读；R3 复核前同此办理。

**编译降级专项条款**（条件触发：`compile_mode=external`，2026-09 批次 4；摘要 ≤1 页与正文页数为官方/红线硬约束，降级模式下由本条款兜底为交付前 ERROR 级门）：交付前编排器逐项确认——①最新 `paper.tex` 对应的用户回传件 `.aux`/`.log`/`.pdf` 三件齐备且同源（同一轮外部编译），缺件不得交付；②以回传件补跑 `check_latex_compliance.py`，ERROR 清零；③若 `.aux` 缺失或无 `abstract:end` 锚点：摘要 ≤1 页与正文页数（≥10 且尽量 ≤30）改为 PDF 人工实测——pymupdf 渲染摘要页与附录起始页 PNG 存 `decision_logs/page_check_evidence/`，实测结论（摘要页数 / 正文起止页 / 正文页数）写入 `decision_logs/manual_page_check.md`，无实测记录不得交付；④补跑与实测完成后删除项目根 `.aux`/`.log` 等编译副产物（`paper.pdf` 保留），再执行工作区卫生与打包终扫。

## 5. 质量红线执行协议（状态机守卫）

subagent 返回后，编排器按 `AGENTS.md` 质量红线节逐项核验（产物存在性以 check_pipeline_manifest.py 结果为准），结果登记 `redline_results`：

- 红线通过 → 更新 pipeline_state.json，推进状态机。
- 红线不过 → 比赛模式：通知用户并暂停；训练模式：记录缺失项后继续（复盘中标注）。
- **红线不过而推进**是编排器违约，复盘时按 decision_logs 与 pipeline_state.json 对账追责。

## 6. HG 退回协议与重试

- **HG 退回**：退回对象 = 本阶段责任 subagent；反馈载体 = 在原 handoff_notes 追加"HG退回反馈"节（日期 + 退回理由 + 整改要求）；退回重跑后重新过同一 HG 门。**轮次衔接**：HG1/HG2 退回时修复回路尚未开始，修复回路轮次按初始状态处理；若退回发生在修复回路已消耗轮次之后，修复回路轮次计数不重置——**禁止借退回重置 R1/R2 上限**。
- **重试**：subagent 崩溃或强制产出缺失 → 重试 ≤2 次（同一调用 prompt + 补充失败信息）；仍失败：比赛模式通知用户，训练模式记录后继续。

## 7. BLOCKED 回退协议

- 回退对象判定：建模根源性错误 → MODELING；数据/数据理解错误 → MODELING；其余按标记内容归属。
- **首次实际回退必须演练化记录**：回退执行后，将触发者、原因、回退对象、重跑结果、耗时写入 `blocked_history`——回退通道的存在性以"被走通过并记录"为验证标准。
- 训练模式 BLOCKED 不回退属规则允许（仅记录），但复盘时必须评估"若比赛模式此处是否应回退"。

## 8. 复盘组织协议（并行）

1. 确认 REVIEW_FIX/CALIBRATION 全部机查报告齐备（第 4 节），并**运行 `check_machine_checks.py`（复盘前必跑）**对账全程 `machine_checks` 登记与报告文件——虚报/漏跑/陈旧报告 ERROR 清零方可进入复盘，否则复盘结论建立在虚假执行证据上。
2. **圈定本轮可共享材料清单**：按 `AGENTS.md` 信息隔离节白名单，逐个列出本轮可读文件的具体路径（含校准产出物【可共享节】位置）；清单作为 handoff 契约第五项写入每个复盘调用 prompt。
3. **同一消息内并发发起四个复盘 Task**（并行兼容性矩阵白名单），每个调用 prompt 显式下发该清单并声明"清单外一律禁读"。白名单材料均为复盘前已固化产物，四任务并行无读写冲突。
4. 收齐后、汇总前，**重跑 `check_isolation.py`（复盘后内容泄漏审计）**——此时 retro_*.md 已生成，脚本检查 2 的非授权产出扫描才真正生效；ERROR 清零方可汇总，报告更新 `isolation_check_report.json` 并登记 `machine_checks`。
   **签名规程（签名缺失 = 审计未执行）**：每次调用必须携带 `--signature`。特征串由编排器在首次泄漏审计前从 `decision_logs/_quarantine/` 提取物中现场提取 ≥3 条高区分度片段（参照论文标题短语 / 专有数值 / 特有术语，每条 ≥10 字符，禁止取自赛题本身公开内容），登记 `pipeline_state.json` 顶层字段 `isolation_signatures`（见 §3 字段表，不并入 machine_checks 条目结构）后供 CALIBRATION→RETRO 与复盘后两次审计复用；未登记签名而运行的审计记录视为无效，须补签名重跑。
5. 串行汇总 retrospective.md；含参照论文信息的节按惯例 C-1 分层标注。
6. 汇总总审批清单 → 提交用户逐项审批 → 审批通过后按铁律 6 执行写入 + 回读 + **git commit（含批次号）**。

## 9. 审批落地协议

审批通过 → 逐字写入目标共享文件 → @calibration-analyzer 回读（附 diff 证据）→ git commit（message 格式：`[审批批次号] 规则落地：简述`）→ commit 哈希写入落地记录。**禁止先写入后补批。**

## 10. 变更管理

本文件的修改须与 `AGENTS.md` 同步评审（两文件共同构成编排真相）；新增机查脚本须在 code_templates/ 注册并在本文件第 4 节表格登记执行时机。
