# 产物注册表（唯一注册源）

> 本表是流水线全部具名产物的唯一注册源：名称 / 规范路径 / 生产者 / 消费者 / 产出阶段 / 必填性。
> 机查脚本 `.trae/code_templates/check_pipeline_manifest.py` 解析本表执行齐备性检查——**表结构（列名与顺序）不得改动**，产物增删只能增删数据行。
> 路径一律相对项目根。产出阶段序：intake < modeling < method < figures < writing < review < compliance。必填性：必填 / 条件（附条件说明）。

| 名称 | 规范路径 | 生产者 | 消费者 | 产出阶段 | 必填性 |
|------|---------|--------|--------|---------|--------|
| 题面.md | 赛题/题面.md | 编排器（HG0 转写） | modeling-solver / METHOD / FIGURES / paper-writer / reviewer / 编排器 | intake | 必填（≥200 字原文转写，禁止改写） |
| ingest_report | 赛题/ingest_report.json | 编排器（HG0 转写） | 编排器 | intake | 必填 |
| 题面附件转写 | 赛题/附件/ | 编排器（HG0 转写） | modeling-solver / METHOD / FIGURES / paper-writer / reviewer | intake | 条件（说明类 .docx/.doc 源文件存在时） |
| 题面图 | 赛题/题面图/ | 编排器（HG0 转写） | modeling-solver / FIGURES / paper-writer / reviewer | intake | 条件（PDF 含嵌入图或疑似扫描页时） |
| solution.json | result_bundle/solution.json | modeling-solver | METHOD / paper-writer / reviewer | modeling | 必填 |
| modeling_plan.json | result_bundle/modeling_plan.json | modeling-solver | METHOD / paper-writer / reviewer | modeling | 必填 |
| feature_fingerprint.json | result_bundle/feature_fingerprint.json | modeling-solver | modeling-solver（内部）/ METHOD / 编排器（机查） | modeling | 必填 |
| 术语表.json | result_bundle/术语表.json | modeling-solver | paper-writer | modeling | 必填（唯一路径，禁止双份并存） |
| handoff_notes_1 | handoff_notes_1.md | modeling-solver | 编排器 / paper-writer / FIGURES / METHOD | modeling | 必填 |
| rework_brief.md | decision_logs/rework_brief.md | 编排器 | modeling-solver / 编排器 | modeling | 条件（MODELING 回退实际发生、rework_brief_active 时） |
| rework_brief.json | decision_logs/rework_brief.json | 编排器 | modeling-solver / 编排器 | modeling | 条件（MODELING 回退实际发生、rework_brief_active 时） |
| contract_check_report | contract_check_report.json | 编排器（机查） | 编排器 / paper-writer | modeling | 必填 |
| modeling_artifacts_report | modeling_artifacts_report.json | 编排器（机查） | 编排器 | modeling | 必填（绝对路径/商业求解器/指纹契约 + P11-N 过早出图；orchestrator §4 MODELING 门，须先于 manifest 执行） |
| code_hygiene_report | code_hygiene_report.json | 编排器（机查） | 编排器 | modeling | 必填（交付代码注释卫生；orchestrator §4 MODELING 门，须先于 manifest 执行） |
| leakage_check_report | leakage_check_report.json | 编排器（机查） | 编排器 | modeling | 条件（仅 problem_track=stats） |
| workspace_hygiene_report | workspace_hygiene_report.json | 编排器（机查） | 编排器 | modeling | 必填（具名门执行：intake/modeling/method/figures/writing/review/compliance；最早于 intake 产出；须先于该门 manifest） |
| method_critique.md | decision_logs/method_critique.md | 编排器（METHOD） | HG1 / paper-writer | method | 必填（闸门+天花板；不占 handoff_notes 编号；reviewer 不读） |
| method_critique.json | decision_logs/method_critique.json | 编排器（METHOD） | 编排器（红线）/ paper-writer | method | 必填（verdict ∈ PASS / PASS_WITH_NOTES / BLOCKED；BLOCKED 或未裁决的 PASS_WITH_NOTES 不得启动 FIGURES） |
| figures 目录 | result_bundle/figures/（≥6 张 PDF+PNG 双格式） | 编排器（FIGURES） | paper-writer / reviewer / HG1 | figures | 必填 |
| 图表清单 | result_bundle/图表清单.md | 编排器（FIGURES） | paper-writer / reviewer / HG1 | figures | 必填 |
| figures_artifacts_report | figures_artifacts_report.json | 编排器（机查） | 编排器 | figures | 必填（P11-F 双格式配对 + P11-V visual_qa；orchestrator §4 FIGURES 门，须先于 manifest 执行） |
| paper.tex | paper.tex | paper-writer | reviewer | writing | 必填 |
| paper.pdf | paper.pdf | paper-writer（降级模式：用户外部编译回传） | reviewer | writing | 必填（compile_mode=external 时缓办：用户回传 .aux/.log/.pdf 三件齐备，COMPLIANCE 前仍缺 → ERROR；见 orchestrator §4 编译降级专项条款） |
| abstract_candidates | decision_logs/abstract_candidates.md | paper-writer | reviewer / 编排器 | writing | 必填（≥2 版） |
| handoff_notes_2 | handoff_notes_2.md | paper-writer | 编排器 | writing | 必填 |
| latex_compliance_report | latex_compliance_report.json | 编排器（机查） | 编排器 / reviewer | writing | 必填 |
| latex_env_report | latex_env_report.json | 编排器（机查） | 编排器 | writing | 必填（WRITING 启动前预检产出：xelatex/关键宏包/中文字体；须先于 manifest 执行） |
| tex_number_check_report | tex_number_check_report.json | 编排器（机查） | 编排器 / reviewer | writing | 可选（WARN 级辅助：tex 正文数值 vs solution.json 一致性） |
| review_report | decision_logs/review_report.json | independent-reviewer | paper-writer / 编排器 | review | 必填 |
| review_scores | decision_logs/review_scores.md | independent-reviewer | 编排器 | review | 必填 |
| handoff_notes_3 | handoff_notes_3.md | independent-reviewer | 编排器 / paper-writer | review | 必填 |
| fix_round1 | decision_logs/fix_round1.md | paper-writer | reviewer / 编排器 | review | 条件（修复轮实际发生时） |
| fix_round2 | decision_logs/fix_round2.md | paper-writer | reviewer / 编排器 | review | 条件（进入第 2 轮时） |
| fix_points_round1 | decision_logs/fix_points_round1.md | 编排器 | reviewer | review | 条件（R1 复审前生成；orchestrator §4 复审修复点 diff 协议） |
| fix_points_round2 | decision_logs/fix_points_round2.md | 编排器 | reviewer | review | 条件（R2 复审前生成，同上） |
| manifest_check_report | manifest_check_report.json | 编排器（机查） | 编排器 | review | 必填（每次阶段转换更新） |
| packaging_report | packaging_report.json | 编排器（机查） | 编排器 | compliance | 必填（COMPLIANCE 打包终扫：只收代码+数据+图表，内部契约 JSON 不入包） |
| pipeline_state | pipeline_state.json | 编排器 | 编排器 | modeling | 必填（HG0 创建，全程更新） |

## 历史漂移对账（注册依据）

- handoff_notes 位置三种放法 → 统一项目根，编号连续（1=solver，2=writer，3=reviewer，契约外编号禁止）
- 术语表双份并存 → 唯一路径 result_bundle/术语表.json
- 审批清单 / retro_* / calibration_* 不属活流水线产物
- 复盘文件 retrospective_* 误命名 → 活流水线不应出现；若出现视为契约外
- fix_round3 及以上 → USER_CLEANUP 态产物，命名 user_cleanup.md（若发生），不占 fix_round 编号
- figures / 图表清单从 modeling 拆出 → 产出阶段 figures；图表清单唯一路径 result_bundle/图表清单.md
- 方法学批评从 solver 自检拆出 → 产出阶段 method；METHOD 为编排器专项，不占 handoff_notes 编号
- 赛题 PDF 由各 agent 现场 pymupdf 抽取 → HG0 一次转写，唯一阅读入口 赛题/题面.md
- 建模返工工单 → 唯一路径 decision_logs/rework_brief.md 与 .json；再次回退覆盖；禁止 rework_brief_2 一类编号，不占 handoff_notes
- s1/s2/s3/s4 反思日志、guided_questions_trace、method_card_matching 不再是活流水线必填；旧题目录里留着也不判契约外。方法卡片仍是库，不要求逐张点名日志
