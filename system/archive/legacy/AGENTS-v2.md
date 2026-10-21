# 数模 B 题智能体流水线（v2.0）

> **框架 v3 设计（Phase 0）**：目标运行框架见 [`system/framework.md`](system/framework.md)，机器可读规格见 [`system/framework.json`](system/framework.json)。Phase 0 只新增规格与迁移计划，**不改变本文件现行规则**；迁移矩阵见 [`system/migration-map.md`](system/migration-map.md)。

## 启动确认

活流水线**只有比赛模式**（HG 门 + R1-R2 + 合规交付）。对标获奖论文、复盘进化见仓库根目录 `进化工具包/`（比赛前整夹移走）。

启动时主智能体必须向用户确认四件事：**项目根路径、题型轨 `problem_track`（`opt` / `stats`）、赛制剖面**（`cumcm` / `shuwei_zh` / `shuwei_en`）、**题面是否齐备**。赛制未选或非法值视为 `cumcm`。`problem_track` 没有缺省：缺失或非法值不得进入 MODELING。

- HG0 题型判定：优化/运筹类 → `opt`，调用 `modeling-solver-opt`；数据驱动/统计/仿真类 → `stats`，调用 `modeling-solver-stats`。不得再转场到别的仓库，也不得把数据题降成「知识库降一级」后仍用优化岗。
- 混合题：①只有拟合模型上的参数寻优、没有结构性决策变量 → `stats`；②结构化优化子问构成题面主体（不少于半数子问，或题面核心任务）→ `opt`；③个别「最优/最短」或寻优依附拟合 → 不因此改成 `opt`。只跑一条主干。对侧只能点名借具体文件，清单写入 `handoff_notes_1.md`。禁止把对侧卡片目录整夹放进必读。
- 调用建模岗时，上游清单必须写明本轨的求解器名、卡片目录、专项惯例和指纹模板，取值从 `.trae/code_templates/track_manifest.json` 抄，不得改判。

## 团队

| Subagent | 职责 | 投入时机 |
|------|------|------|
| @modeling-solver-opt | 优化/运筹：读题→建模→求解→灵敏度→打包 | `problem_track=opt` |
| @modeling-solver-stats | 数据/统计：读题→建模→求解→验证→打包 | `problem_track=stats` |
| @paper-writer | 读取 result_bundle（含已成图）→ 写 LaTeX → 编译 PDF → 自审 → **接收评审反馈执行修复（R1-R2）** | METHOD、FIGURES 与 HG1 之后 |
| @independent-reviewer | 盲审五维度评分 → 本轨 12 项核查 → 双盲 → **复审修复轮** | paper.pdf 产出后 |

活智能体只有上表四名。不要再登记 `modeling-solver`。写作岗与评审岗各一个，不按轨再拆。

**编排器专项 METHOD**（非独立团队 agent，不占 handoff_notes 编号）：modeling-solver 红线通过后、FIGURES 前，编排器另起干净上下文做方法学批评（协议见 `.trae/rules/orchestrator.md` METHOD 专项）。禁止把本岗塞进 solver / writer / reviewer / FIGURES。

**编排器专项 FIGURES**（非独立团队 agent，不占 handoff_notes 编号）：METHOD 红线通过后、HG1 前，编排器另起干净上下文出图（协议见 `.trae/rules/orchestrator.md` FIGURES 专项）。禁止把出图塞进 solver / writer / reviewer。

主智能体（编排器）为一等实体：显式状态机、门控协议、机查执行义务、重试与回退协议见 `.trae/rules/orchestrator.md`，本文件不再以散文重复定义编排职责。

## 开放检索（比赛模式）

比赛中任何 agent（含编排器 METHOD / FIGURES 专项）**应主动检索**有助于建模、求解、写作与核验的公开资料，包括同题/同类往年论文、MCM/ICM outstanding、教材、手册与代码。WebSearch / WebFetch **不设同题禁令**。读到的方法须化为本题变量与约束，引用进论文须可查证（DOI 或出版社页面）。

仍禁止：①把同题特定信息写入共享文件（`.trae/`、`AGENTS.md`、惯例卡，见「防过拟合铁律」）；②把 `数模C题专家团` 当作方法来源或去读该仓赛题产物；③无出处地复述他人公式与数值。

读题入口仍是 `赛题/题面.md`，不因语言改抽 PDF。

## 时间预算（约 72h）

各阶段起止时间戳统一记录于 `pipeline_state.json` 的 `stage_timestamps` 字段（读写协议见 orchestrator.md）——耗时记录的唯一载体，禁止散落于散文日志。

| 阶段 | 时间盒 | 压缩预案（超时时） |
|------|:---:|------|
| 读题 + 建模（含 S1/S2） | ≤20h | 多模型候选从 ≥2 降为 1+备选说明 |
| 求解 + 验证（含 S3，**不含出图**） | ≤14h | 多算例从 ≥2 降为 2 个代表性场景 |
| 方法学批评（METHOD） | ≤2h | 升级票从 2 降为 1；闸门四问不减 |
| 出图（FIGURES） | ≤4h | hero 打磨、其余配方直出 |
| 论文写作（含 S4/自审） | ≤18h | 图表解析段落保 150 字底线，不扩展 |
| 评审⇄修复（≤2 轮） | ≤10h | 第 2 轮后残留项交 HG3 裁决 |
| 摘要精修 + 合规 + 提交 | ≤10h | **不可压缩**（提交合规是硬约束） |

任一阶段预计超时 30% → 主智能体通知用户并给出压缩方案；**验证项（最优性验证、模型验证、灵敏度分析）任何情况下不得删除**。

## 编排顺序（9 步，逐门暂停）

1. **HG0 准入**：赛题转写（`convert_problem.py` → `赛题/题面.md`）+ 题型判定 + 赛制剖面 → **暂停等用户确认**
2. **本轨建模岗**（`modeling-solver-opt` 或 `modeling-solver-stats`）→ 产出 result_bundle/（不含 figures）+ handoff_notes_1.md
3. **METHOD**（编排器专项方法学批评）→ `decision_logs/method_critique.md` + `method_critique.json`。完成后编排器必须给出推荐方案再停等你拍板：`BLOCKED` 荐回退；无升级票荐出图；有升级票荐「放行出图」或「按某张票回退 solver」。禁止先画图再问，禁止只列选项不推荐
4. **FIGURES**（编排器专项出图）→ `result_bundle/figures/` + `图表清单.md`
5. **HG1 用户审查**（按审查卡，建模+求解+方法学批评+成图一次审查）→ 放行/退回
6. **@paper-writer** → 产出 paper.pdf + paper.tex + 摘要候选
7. **HG2 用户审查**：确认论文初稿 → 放行/退回
8. **@independent-reviewer 初审** → **修复回路 R1-R2**（paper-writer 修复 ⇄ reviewer 复审，≤2 轮）→ **HG3 用户裁决**
9. **合规检查 + 摘要定稿** → 交付

失败（红线不过、subagent 崩溃且重试耗尽、BLOCKED）一律**通知用户并暂停**，禁止记录后继续。

## 并行

主线 solver / writer / reviewer 禁止并行（产物依赖 + 盲审独立）。METHOD 与 FIGURES 不得与 MODELING / WRITING / REVIEW 并行，二者之间也不得并行。Subagent 内部并行不受限。

## HG 审查卡（用户逐项勾选后放行）

- **HG0**：①题型轨 `opt` / `stats` 是否认可？②项目根路径是否正确？③`赛题/题面.md` 是否齐备、抽查公式/表是否可读？④赛制剖面（`cumcm` / `shuwei_zh` / `shuwei_en`）是否认可？⑤混合题若借对侧文件，借卡清单是否认可？
- **HG1**：打开 `track_manifest.json` 里本轨的 `hg1_card`，逐项勾选。**退回分流**：数值、模型或换方法 → 本轨建模岗（先写 `rework_brief`）；图面 → 重跑 FIGURES。
- **HG2**（论文初稿）：①摘要四要素 + 一页以内？②符号说明与术语表一致？③图表 ≥6 且无凑数图；正文引用的图型/颜色/子图标签与 PDF 是否一致（人看 PDF）？④`opt`：最优性或蒙特卡洛子节独立存在；`stats`：交叉验证或过拟合自查子节独立存在？**`shuwei_en` 另核**：⑤Summary 后第 2 页为目录？⑥正文页眉 `Team #` 与 `Page x of y`？⑦图轴/caption 为英文且与 PDF 一致？
- **HG3**（评审后裁决）：①红队 high severity 问题是否全部修复或合理反驳？②两轮后残留问题是否接受？③是否触发 BLOCKED 回退本轨建模岗？

## 修复回路（R1-R2）

1. reviewer 初审输出 review_report.json + review_scores.md
2. paper-writer 逐条处置：接受修复（fixed）/ 反驳（rejected + 具体理由），原地修改 paper.tex 并重编译 → 输出 `decision_logs/fix_round{N}.md`（每条：问题 → 处置 → 修复位置）
3. reviewer 复审：**仍全文通读**（禁止增量评审），重点验证已修复项是否真修复、是否引入跨节新错 → 更新 review_report.json（标注轮次）。若修复涉及数值改动、段落拆分或内容移位，除逐项验证修复点外，须对修复点所在小节做全节数值重算（不限于工单列出的数值）
4. 仍有 high severity → 进入第 2 轮；**最多 2 轮**
5. 第 2 轮后仍残留 high severity → HG3 用户裁决
6. 修复仅限表达/一致性/遗漏补充；发现建模根源性错误 → 标记 BLOCKED，回退 modeling-solver（需用户确认；编排器按 orchestrator.md §7 写 `rework_brief` 后再调 solver）。**图面级修复**（数值不变、仅图面表达层重绘）属"表达"范畴，**由编排器按 FIGURES 专项重跑**（覆盖 `project/figures/` 与 `result_bundle/figures/`）；paper-writer 只改 caption / 解析段 / `\includegraphics` 路径，禁止重绘、禁止 Read 生成图。缺陷根源为数值错误时仍走 BLOCKED 回退 modeling-solver
7. **R1 工单执行强制**（2023B 校准反馈，通用规则）：R1 修复工单未全部执行（或逐项显式记录不执行理由）不得进入下一阶段。

## 红队自查机制（努力举证制，全 agent 通用，一处定义）

各 agent 红队自查**不设问题数配额**，实行努力举证制：须完整执行本 agent 指定的红队检查范围（范围在各 agent 文件中注明），并在对应日志中书面记录**搜查范围与证据**（搜查对象清单 + 每对象检查结论）。

- 找出 high severity 问题：全部记录（问题描述 + 位置 + 影响 + 处置）。
- 找出 0 个 high severity：凭搜查范围与证据记录即判定通过，**禁止凑数**。
- **虚惊标注**：若某条 high severity 在自检后判定为"形式合规但实际风险远低于所标级别"，须显式标注 `[虚惊]` 并说明降级理由（如"已通过另一层检查覆盖""实际影响有限"）。虚惊率明显偏高时由用户确认是否调整检查范围。

**禁止虚构 high severity 问题**——虚构的高危问题比遗漏更危险。

## 防过拟合铁律（写入任何共享文件前必须逐条自查）

对话改进时读 `进化工具包/README.md`（完整自查清单在该文件）。**活流水线禁止改共享文件**（`.trae/agents/`、`.trae/papers/`、`.trae/code_templates/`、`rules/`），除非用户当场要求。

## handoff 契约

- 产物的名称 / 规范路径 / 生产者 / 消费者 / 产出阶段以 `.trae/papers/产物注册表.md` 为**唯一注册源**；阶段转换时由主智能体运行 `.trae/code_templates/check_pipeline_manifest.py` 机查齐备性，不齐不得推进（执行协议见 orchestrator.md）。
- 主智能体每次调用 Subagent，必须在调用 prompt 中显式给出三项：**项目根绝对路径、上游产出清单（路径 + 一句话用途）、本阶段强制产出清单**。建模调用的上游清单必须含本轨求解器名、卡片目录、专项惯例、指纹模板。**返工调用**须在三件套之外加第四块：任务类型=返工；必读 `decision_logs/rework_brief.md`；keep / change / forbidden 从 `rework_brief.json` 原样抄入（协议见 orchestrator.md §7）。返工仍调用本轨那一个建模岗。磁盘上有 brief 但清单未列，不得当返工。
- **result_bundle/ 契约**（solver 产出数值与方案，FIGURES 产出图表，paper-writer 消费，reviewer 核查）：
  - `opt` 的 `solution.json`：每个子问题含 `objective_value`、`decision_variables`、`solver`、`optimality`（MIPGap / 枚举完备性 / 启发式统计）、`active_constraints`（各约束 active/slack + 最优解处派生量数值——slack 量/边际响应/局部灵敏度其一，完整要求见优化专项 优.4）、`sensitivity`、`critical_points`（临界点 + source）、`monte_carlo`（次数 / 收敛 / 偏差，不适用则为 null 并说明）
  - `stats` 的 `solution.json`：每个子问题含 `task_type`、`objective_or_goal`、`metrics`、`model.selection`（含基线）、`validation`（含 `overfitting_check`）、`preprocessing`（含 `train_test_isolation`）、`data_lineage`、`sensitivity`、`monte_carlo`（不适用则为 null 并说明）
  - `opt` 的 `modeling_plan.json`：含 `design_critique`、`cost_decomposition`、`alternative_algorithm_discussion`、`joint_constraint_check`
  - `stats` 的 `modeling_plan.json`：含 `design_critique`、`data_feasibility`、`leakage_check`；有下游决策时含 `downstream_decision_kind`
  - `feature_fingerprint.json`、`术语表.json`（modeling-solver）
  - `figures/`（PDF+PNG 双格式）与 `图表清单.md`（编排器 FIGURES）
  - `decision_logs/method_critique.md` 与 `method_critique.json`（编排器 METHOD；writer 吸收 NOTES，reviewer 不读以免锚定）
- **赛题转写契约**（编排器 HG0，MODELING 前）：`赛题/题面.md` 为后续 agent 唯一题面阅读入口；说明类附件见 `赛题/附件/`；题面源图见 `赛题/题面图/`。xlsx/csv 数据附件仍按原文件读取，不转写。禁止各 agent 自行对赛题 PDF 做 pymupdf 抽取。
- **支撑材料卫生契约**（2026-08 批次 2026-08-B1）：modeling-solver 负责产出时代码注释不含内部流程词（黑名单见 `check_code_hygiene.py`，MODELING 过门机查）；编排器在 COMPLIANCE 阶段运行 `package_support_materials.py` 一键打包并终扫（只收代码+数据+图表，内部契约 JSON 一律不入包）；**不新增打包 agent**
- **工作区卫生契约**（2026-08 批次 2026-08-B2）：临时脚本与测试文件用完即删；result_bundle/ 内文件禁止在项目根重复存在；LaTeX 编译副产物不得滞留工作区；机查见 `check_workspace_hygiene.py`（编排器在各具名阶段转换门执行，ERROR 清零方可推进）
- **pipeline_state.json 为编排器专属读写**：任何 Subagent 禁止创建/修改/删除该文件（状态唯一载体协议见 orchestrator.md §3）。
- Subagent 崩溃或强制产出缺失 → 主智能体重试 ≤2 次；仍失败：立即通知用户并暂停。

## 质量红线（每个 Subagent 完成后由编排器状态机守卫执行：红线不过不得推进，通知用户并暂停）

红线是**关卡**而非散文义务：编排器按 orchestrator.md 协议逐项核验并登记 pipeline_state.json，缺失产物同时触发 check_pipeline_manifest.py ERROR。

- **本轨建模岗**：result_bundle/solution.json 存在且非空，且 modeling_plan.json、feature_fingerprint.json、术语表.json、handoff_notes_1.md 齐全。不要求反思日志或方法卡片匹配矩阵。`stats` 另须已跑 `check_leakage.py` 并留下 `leakage_check_report.json`。`opt` 不要求该报告
- **METHOD**（编排器专项）：`decision_logs/method_critique.md` 与 `method_critique.json` 存在；JSON 含合法 `verdict` 与 `recommend`；`BLOCKED` 或未裁决的 `PASS_WITH_NOTES` 不得启动 FIGURES
- **FIGURES**（编排器专项）：result_bundle/figures/ ≥6 组 PDF+PNG + result_bundle/图表清单.md 存在 + `visual_qa.py scan` 无 ERROR
- **@paper-writer**：**正文（摘要页之后、不含附录）≥10 页且 ≤30 页**（>30 为 WRITING 门 ERROR，压缩前不得进 HG2）+ 图表引用 ≥6 处 + abstract_candidates.md ≥2 版。**`shuwei_en`**：Summary+目录+正文 ≤25（官方无下限），不套本条 10–30
- **@independent-reviewer**：五维度均有 ≥3 句具体依据 + B 题 12 项核查齐全 + 红队搜查范围与证据记录（含虚惊标注）。**评审红线只约束评审行为，不设分数下限**——低分是论文信号，如实报告是评审职责；评分仅作为修复回路触发信号

## 合规检查（交付前，reviewer 附带核查 + 主智能体确认）

- **正文 ≤30 页**（摘要页之后起算，附录不计页数；>30 为 ERROR）。官方表述为正文"尽量控制在 20 页以内"；30 页是本团队硬上限，冲高档次建议压向 20 页附近
- **摘要 ≤1 页**（官方硬约束）
- 全文（含附录、图表、代码注释）无学校 / 队员 / 赛区 / 导师信息
- 参考文献可查证（DOI 或出版社页面可达）
- 附录含完整可运行源程序（缺一取消评奖资格，属硬约束）
- 文件命名、支撑材料打包、MD5 生成按当年竞赛通知执行（主智能体提醒用户，**MD5 生成后不得再改文件**）
- 排版优先采用当年官方模板；自排版须逐项对照官方格式规范复核

## 严禁

- 跳过用户审查自动推进
- **存在信息依赖的 agent 对并行执行**（见"并行"节；Subagent 内部并行不受限）
- 代写任何 Subagent 的专业产出。METHOD 与 FIGURES 是编排器专项：禁止用当前会话兼做，必须另起干净 Task
- 把 `数模C题专家团` 的赛题产物、参照论文或提取物当作本仓输入
- **Read 生成图**：solver / writer / METHOD / FIGURES 专项禁止 Read 生成图（PNG/PDF/WebP：`result_bundle/figures/`、`project/figures/`、论文编译页截图）。`visual_qa.py` 程序自检除外。**允许** Read `赛题/题面图/`。**reviewer 核图文白名单**：仅可 Read `result_bundle/图表清单.md` 列出的 `result_bundle/figures/*.png`，只核图文是否矛盾，不得改图、不得 Read 编译页截图。遮挡/字号/对齐仍交 HG1（PNG）与 HG2（PDF）人工。
- **将同题特定信息写入任何共享文件**（防过拟合铁律）
- **虚构红队 high severity 问题凑数**（见"红队自查机制"节）
- 删除验证项（最优性验证 / 模型验证 / 灵敏度分析）来赶进度
