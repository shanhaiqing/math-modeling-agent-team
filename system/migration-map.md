# 迁移矩阵：Trae 现行系统 → DSH 运行框架 v3

> 用途：证明现行系统的每一项资产、每一条规则都有新家，**不留 orphan**。
> 原则：不换产物路径、不重写知识资产、角色 prompt 瘦身为 skills、orchestrator 散文退役为 Kernel 配置。
> **Phase 0 只新增 `system/` 与根目录指针，不移动/修改下列任何现有资产。**

---

## 1. 资产矩阵

### 1.1 顶层与规则

| 现有资产 | 现行作用 | 新家 / 处置 | 处置 | Phase |
|---|---|---|---|---|
| `AGENTS.md`（17.5KB） | 活流水线唯一真相：团队、门、契约、红线 | 瘦身为 ≤2KB 路由 + 不变量；细节进 `system/framework.md` + skills | rewrite | Phase 2 |
| `.gitignore` | 忽略 .venv/LaTeX 副产物/演练产物 | 追加 `runs/`；其余保留 | keep+extend | Phase 0 |
| `requirements.txt` | Python 依赖清单 | 保留；Phase 1 可视需要补 `jsonschema`（仅测试用，非运行必需） | keep | Phase 1 |
| `.venv/` | 本地 Python 环境 | 保留；Kernel 默认 `{repo}/.venv/Scripts/python.exe` | keep | Phase 1 |
| `desktop.ini` | Windows 目录显示配置 | 忽略，不迁移 | ignore | — |
| `系统框架图.png` | 用户手绘 v2 协作流程图 | 作为 legacy 参照；v3 图见 `framework.md` §3/§4；不复制、不覆盖 | archive-reference | Phase 0 |
| `code_hygiene_report.json` | 旧运行残留（引用已删除的 `数维杯测试/`） | 归档/删除；不在新框架内使用 | retire | Phase 1 |
| `进化工具包/`（当前不在仓内） | 赛后校准/复盘 | 独立目录；消费 `run_report.json`，不入活流水线 | keep-separate | Phase 4 |

### 1.2 角色与编排

| 现有资产 | 现行作用 | 新家 / 处置 | 处置 | Phase |
|---|---|---|---|---|
| `.trae/rules/orchestrator.md`（22.8KB） | 状态机、pipeline_state、门控、机查、重试、回退 | 状态机/机查表/预算 → `framework.json` + `checks.json` + Kernel；散文退役 | rewrite | Phase 1-2 |
| `.trae/agents/modeling-solver-opt.md` | opt 建模求解 prompt | `skills/solver-opt/SKILL.md`（≤4KB）+ references（决策树/惯例/卡片） | rewrite | Phase 2 |
| `.trae/agents/modeling-solver-stats.md` | stats 建模求解 prompt | `skills/solver-stats/SKILL.md` + references | rewrite | Phase 2 |
| `.trae/agents/paper-writer.md`（18KB） | 论文写作 + 修复回路 prompt | `skills/paper-writer/SKILL.md` + references（结构/规范/去AI味/摘要） | rewrite | Phase 2 |
| `.trae/agents/independent-reviewer.md`（18KB） | 五维 + 12 项 + 红队 + 复审 prompt | `skills/independent-reviewer/SKILL.md` + references（检查单/规范） | rewrite | Phase 2 |
| `.trae/agents/modeling-solver.md`（336B stub） | 旧单轨入口，已废弃 | 退役；不再登记 | retire | Phase 2 |
| `.trae/agents/calibration-analyzer.md` | 已删除（git status 显示 D） | 不恢复；校准能力归进化工具箱 | retire | — |
| `.trae/rules/` 其他文件 | 当前仅 orchestrator.md | 全部并入 `system/` | move | Phase 2 |

### 1.3 知识资产（`.trae/papers/`）

| 现有资产 | 现行作用 | 新家 / 处置 | 处置 | Phase |
|---|---|---|---|---|
| `产物注册表.md` | 唯一产物注册源；manifest 解析 | `framework.json.artifacts` 为 canonical；Markdown 视图生成；Phase 2 切换解析器 | rewrite-source | Phase 2 |
| `国赛公开惯例.md`（34KB） | 跨题方法/写作/评审惯例 | `knowledge/conventions/cumcm.md`；保留条款编号与目录；按 skill 检索 | move+index | Phase 2 |
| `优化专项惯例.md` | opt 专项条款 | `knowledge/conventions/opt.md` | move | Phase 2 |
| `数据题专项惯例.md` | stats 专项条款 | `knowledge/conventions/stats.md` | move | Phase 2 |
| `优化问题分类决策树.md` | opt 主类型判定 | `knowledge/trees/opt.md` | move | Phase 2 |
| `数据问题分类决策树.md` | stats 任务类型判定 | `knowledge/trees/stats.md` | move | Phase 2 |
| `论文分类索引.md` | 题型→论文检索 | `knowledge/index/papers.md` | move | Phase 2 |
| `优化方法卡片/`（12 张） | opt 方法库（可否决） | `knowledge/cards/opt/` | move | Phase 2 |
| `数据方法卡片/`（13 张 + README） | stats 方法库（可否决） | `knowledge/cards/stats/` | move | Phase 2 |
| `评审检查单_opt.md` / `_stats.md` | reviewer 本轨 12 项 | `knowledge/review/checklist-opt.md` / `checklist-stats.md` | move | Phase 2 |
| `HG1审查卡_opt.md` / `_stats.md` | G2 人工审查卡 | `system/gates/G2-model-figures.md` + 本轨卡片 | merge | Phase 2 |
| `LaTeX格式规范.md` | 论文排版硬约束 | `knowledge/writing/latex.md` | move | Phase 2 |
| `摘要写作规范.md` | 摘要审计门 | `knowledge/writing/abstract.md` | move | Phase 2 |
| `去AI味写作规范.md` / `_en.md` | 语言自然度 | `knowledge/writing/anti-ai.md` / `anti-ai-en.md` | move | Phase 2 |
| `图表类型参考库.md` | 图型决策表/设计规范 | `knowledge/figures/chart-reference.md` | move | Phase 2 |
| `博弈论论证规范.md` | 条件触发专项 | `knowledge/special/game-theory.md` | move | Phase 2 |
| `visual_anchors/流程图.png` | 视觉参照 | `knowledge/figures/visual-anchors/` | move | Phase 2 |

### 1.4 技能与脚本

| 现有资产 | 现行作用 | 新家 / 处置 | 处置 | Phase |
|---|---|---|---|---|
| `.trae/skills/method-studio/SKILL.md` | 方法学批评工作流 | `skills/method-critic/SKILL.md` | move+rename | Phase 2 |
| `.trae/skills/method-studio/gate_opt.md` | opt 闸门四问 | `skills/method-critic/gate-opt.md` | move | Phase 2 |
| `.trae/skills/method-studio/gate_stats.md` | stats 闸门四问 | `skills/method-critic/gate-stats.md` | move | Phase 2 |
| `.trae/skills/figure-studio/SKILL.md` | 出图 6 步工作流 | `skills/figure-studio/SKILL.md` | move | Phase 2 |
| `.trae/skills/figure-studio/recipes/`（8 个） | 图型配方 | `skills/figure-studio/recipes/` | move | Phase 2 |
| `.trae/skills/figure-studio/references/`（3 个） | 设计/视觉/TikZ 规范 | `skills/figure-studio/references/` | move | Phase 2 |
| `.trae/skills/figure-studio/scripts/visual_qa.py` | 零 token 图面自检 | `skills/figure-studio/scripts/visual_qa.py` | move | Phase 2 |
| `.trae/skills/reference-studio/SKILL.md` | 文献工作流 | `skills/reference-studio/SKILL.md` | move | Phase 2 |
| `.trae/skills/reference-studio/scripts/citation_check.py` | 引用双向核对 | `skills/reference-studio/scripts/` | move | Phase 2 |
| `.trae/skills/reference-studio/scripts/doi_audit.py` | DOI/URL 可达性 | `skills/reference-studio/scripts/` | move | Phase 2 |
| `.trae/code_templates/*.py`（checkers，见 §2） | 机查/转换/打包 | `tools/checkers/`；Phase 1 Kernel 包装，不改判据 | move | Phase 1 |
| `.trae/code_templates/*_solver.py` / `graph_utils.py` / `data_modeling_template.py` / `monte_carlo_template.py` | 求解模板 | `tools/templates/` | move | Phase 2 |
| `.trae/code_templates/visualization_style.py` | 绘图样式 | `tools/templates/visualization_style.py` | move | Phase 2 |
| `.trae/code_templates/paper_minimal_template.tex` / `paper_shuwei_template.tex` | 论文模板 | `tools/latex/` | move | Phase 2 |
| `.trae/code_templates/shuwei/swmcmthesis.{cls,cfg}` | shuwei_en 文档类 | `tools/latex/shuwei/` | move | Phase 2 |
| `.trae/code_templates/feature_fingerprint_template_opt/stats.json` | 指纹模板 | `system/templates/` | move | Phase 2 |
| `.trae/code_templates/rework_brief_template.{md,json}` | 返工单模板 | `system/templates/`；由 Kernel 填 | move | Phase 2 |
| `.trae/code_templates/pipeline_state_template.json` | 状态模板 | `schemas/run-state.schema.json` + Kernel | rewrite | Phase 1 |
| `.trae/code_templates/method_critique_template.md` | 方法批评模板 | `system/templates/` | move | Phase 2 |
| `.trae/code_templates/review_scores_template.md` | 评审日志模板 | `system/templates/` | move | Phase 2 |
| `.trae/code_templates/calibration_log_template.md` | 校准日志 | 进化工具箱 | move-separate | Phase 4 |
| `.trae/code_templates/s4_reflection_template.md` | 旧 S4 反思 | 退役（S1-S4 已非活流水线） | retire | Phase 2 |
| `.trae/code_templates/track_manifest.json` | 轨道→资产映射 | 并入 `framework.json` 的 track/profile 配置 | merge | Phase 2 |
| `.trae/code_templates/_test_solver/` / `__pycache__/` | 测试临时产物 | 删除/忽略 | retire | Phase 1 |
| `.trae/references/经典模式库.md` | 经典模式参考 | `knowledge/references/classic-patterns.md` | move | Phase 2 |

### 1.5 赛制与运行产物

| 现有资产 | 现行作用 | 新家 / 处置 | 处置 | Phase |
|---|---|---|---|---|
| `赛制/shuwei_en.md` | 数维杯英文赛制卡 | `contest/shuwei_en.md` | move | Phase 2 |
| `pipeline_state.json`（项目根生成） | 编排器状态 | Kernel 生成兼容视图；canonical 为 `run_state.json` | rewrite | Phase 1 |
| `系统框架图.png` | 旧流程图 | 保留为 legacy；v3 图见 framework.md | archive-reference | Phase 0 |
| `.trae/.git_backup/` | 旧 git 备份 | 保持 `.gitignore` 忽略；不迁移 | ignore | — |
| `.trae/papers/visual_anchors/` | 视觉锚点 | `knowledge/figures/visual-anchors/` | move | Phase 2 |
| `__pycache__/`、`*.pyc` | 缓存 | 保持忽略 | ignore | — |

---

## 2. 机查资产处置

| 脚本 | 处置 | 理由 |
|---|---|---|
| `convert_problem.py` | 保留 | 题面转写入口 |
| `check_pipeline_manifest.py` | 保留 | 产物齐备性门 |
| `check_solution_json.py` | 保留 | opt 契约 |
| `check_solution_json_stats.py` | 保留 | stats 契约 |
| `check_modeling_artifacts.py` | 保留 | 指纹/绝对路径/商业求解器/图面 QA |
| `check_code_hygiene.py` | 保留 | 交付代码注释卫生 |
| `check_workspace_hygiene.py` | 保留 | 工作区卫生 |
| `check_leakage.py` | 保留（stats，WARN） | 泄漏启发式 |
| `check_latex_env.py` | 保留 | LaTeX 预检 |
| `check_latex_compliance.py` | 保留 | 论文合规 |
| `check_tex_numbers.py` | 保留（WARN） | 正文数值一致性 |
| `check_abstract_guard.py` | 保留（WARN） | 摘要审计 |
| `check_machine_checks.py` | 保留（fallback） | 证据链对账；Kernel 模式下由 Kernel 直接记录 |
| `package_support_materials.py` | 保留 | 打包终扫 |
| `check_problem_track.py` | 保留 | track 合法性 |
| `check_prompt_budget.py` | 资产维护 | prompt 体积预算 |
| `check_convention_refs.py` | 资产维护 | 惯例引用完整性 |
| `check_viz_tests.py` | 资产维护 | 绘图回归测试 |
| `check_card_refs.py` | 资产维护 | 卡片→模板引用 |
| `check_reflection.py` | 退役 | S1-S4 已非活流水线 |
| `check_isolation.py` | 移入进化工具箱 | 校准提取物隔离 |
| `check_bc_merge_smoke.py` | 退役 | 一次性冒烟 |
| `test_*.py` | 移入 tests/ | 单元/回归测试 |
| `_test_solver/` | 删除/忽略 | 临时测试目录 |

---

## 3. 规则覆盖（AGENTS.md 逐节）

| AGENTS.md 章节 | 新家 | 承载方式 | 是否有 orphan |
|---|---|---|---|
| 启动确认（项目根/题型轨/赛制/题面） | G0 + `framework.json.scope` | 门决策包 + Kernel 预检 | 否 |
| 团队（solver-opt/stats、writer、reviewer） | `framework.json.roles` + §5 | 角色技能 + Team/specialist | 否 |
| 编排器专项 METHOD/FIGURES | `framework.json.stages.METHOD/FIGURES` + gates | METHOD/FIGURES 状态 + 独立 specialist | 否 |
| 开放检索 | §5.4 + skills | 角色技能允许 WebSearch/WebFetch；引用可查证 | 否 |
| 时间预算与压缩 | §11 + `budgets` | Kernel 告警 + 压缩预案 | 否 |
| 编排顺序 9 步 | §4 状态机 | 状态 + 转移 | 否 |
| 并行约束 | `concurrency` | 主链串行；安全准备白名单 | 否 |
| HG0/HG1/HG2/HG3 审查卡 | G0/G2/G3/G4 + `gates/` | 决策包 + 门卡 | 否 |
| 修复回路 R1-R2 | §10.4 + `limits.review_rounds` | Kernel 轮次计数 + reviewer 全文复读 | 否 |
| 红队自查机制 | §10.3 + reviewer skill | 努力举证制 + 报告字段 | 否 |
| 防过拟合铁律 | §10.5 + `guards.protected_paths` | Kernel 守卫 + 人工 waiver | 否 |
| handoff 契约 | §6 + `framework.json.artifacts` | 产物注册 + Kernel 校验 | 否 |
| result_bundle 契约 | §6.3 + 现有 Python 机查 | 结构/语义/齐备性三层 | 否 |
| 赛题转写契约 | `framework.json.paths` + G0 | `convert_problem.py` 唯一入口 | 否 |
| 支撑材料卫生 | COMPLIANCE + `package_support_materials.py` | Kernel 执行 + 终扫 | 否 |
| 工作区卫生 | 各阶段机查 + `check_workspace_hygiene.py` | Kernel 执行 | 否 |
| pipeline_state 专属读写 | §3.3 + Kernel | Kernel 唯一写者；兼容视图 | 否 |
| 质量红线 | §10.2 + 阶段机查 | Kernel/Reviewer 双检 | 否 |
| 合规检查 | §10.2 + COMPLIANCE | 机查 + G5 | 否 |
| 严禁（跳门/代写/并行/虚构/删验证） | §5.4 + §8 + §10 | Kernel guard + 门记录 + reviewer 规则 | 否 |
| R1 工单执行强制 | §10.4 | 工单逐项处置 + Kernel 校验 | 否 |
| 返工 fresh/resume（orchestrator §7） | `freshness_policy` + failure dossier + rework plan | 局部 resume；根因 fresh_dossier + 计划门 + 回归测试；重复失败 → G1/G4 | 否（有意识地变更旧"默认 fresh"） |
| Read 生成图禁令 | §5.4 + skills | 角色禁止；reviewer 白名单 | 否 |
| 断点接管 | §3.3 + Kernel recovery | run_state/events 接管；stale 重跑 | 否 |
| BLOCKED/重试/暂停 | §4.3 + `limits` | 状态 + 上限 + 人裁决 | 否 |

---

## 4. 安全步与已知漂移

### 4.1 迁移前

1. 当前工作树有大量未提交改动（`git status` 显示多个 M/D/??）。**Phase 0 只新增 `system/`、`tools/validate_framework.py`，并在根目录加指针；不动现有资产。**
2. Phase 1/2 开始前：给当前工作树打 tag（如 `pre-dsh-migration`）或整目录备份；从干净基线迁移。
3. 迁移按 Phase 分步，每步跑 `validate_framework.py` + 现有 `check_pipeline_manifest.py`，确保现行流水线仍可运行。
4. 不删除 `.trae/`，直到新 skills/checkers 在演练中通过；保留回退路径。

### 4.2 已知漂移

| 项 | 状态 | 处置 |
|---|---|---|
| `code_hygiene_report.json` 引用已删除的 `数维杯测试/` | 过期 | Phase 1 归档/删除 |
| `.trae/agents/modeling-solver.md` | stub | Phase 2 退役 |
| `.trae/agents/calibration-analyzer.md` | 已删除（git status D） | 不恢复 |
| `.trae/code_templates/__pycache__/`、`_test_solver/` | 临时产物 | Phase 1 清理/忽略 |
| `.trae/papers/visual_anchors/流程图.png` | 视觉参照 | Phase 2 随 knowledge 迁移 |
| `系统框架图.png` | 旧流程图 | 保留为 legacy；v3 图在 framework.md |
| 旧规则"返工默认另起干净 Task" | 有意变更 | 新策略：局部 resume；根因 fresh + 失败档案 + 计划门 + 回归测试；见 `framework.md` §5.2.1/§10.4.1 |

---

## 5. 覆盖验收

- [x] 顶层与规则：AGENTS.md、orchestrator、gitignore、requirements、venv、desktop.ini、系统框架图、code_hygiene_report
- [x] 角色与编排：5 个 agent 文件 + stub + calibration-analyzer
- [x] 知识资产：惯例/专项/决策树/索引/卡片/检查单/HG 卡/LaTeX/摘要/去AI味/图表库/博弈论/visual_anchors
- [x] 技能与脚本：method-studio/figure-studio/reference-studio；全部 checkers/templates/tests
- [x] 赛制与运行产物：shuwei_en、pipeline_state、.git_backup
- [x] 规则覆盖：AGENTS.md 全部章节 + orchestrator 状态机/门控/机查/重试/回退 + R1 工单 + 红队 + 防过拟合 + 合规 + 严禁
- [x] 机查资产：保留/资产维护/退役/移出四类均有去向

**结论：现行系统无 orphan 资产或规则；Phase 0 不执行迁移，只建立目标与验收。**
