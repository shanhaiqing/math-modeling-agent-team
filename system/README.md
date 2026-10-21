# system/ · 数模 B 题运行框架 v3（Phase 0）

> 这是**目标框架**，不是当前运行中的流水线。
> 现行 Trae 流水线仍是根目录 [AGENTS.md](../AGENTS.md) + `.trae/`；Phase 0 不改变其行为。
> 框架规格：`framework.json`；机查清单：`checks.json`；主文档：`framework.md`。

## 5 分钟入口

1. 先读 `framework.md` 的 §0-§4：结论、对旧图的判断、架构、状态机。
2. 再读 §5、§8：角色/模型路由、人机门。
3. 需要落地时读 §12（DSH 映射）和 `migration-map.md`。
4. 想验证设计是否自洽：跑 `python tools/validate_framework.py`。

## 文件地图

| 文件 | 用途 |
|---|---|
| `framework.md` | 详细运行框架（主交付） |
| `framework.json` | 机器可读规格：stages/transitions/gates/roles/artifacts/model_routing |
| `checks.json` | 阶段→机查顺序/命令/报告/阻塞级别 |
| `migration-map.md` | 现行资产与规则的新家；无 orphan 证明 |
| `tabletop-tests.md` | 8 个场景的预期状态轨迹 |
| `gates/G0..G5` | 人机门卡与决策包模板 |
| `schemas/` | 7 个 schema：run_state / gate_decision / artifact_manifest / check_report / cost_report / failure_dossier / rework_plan |
| `team/team-blueprint.md` | 7 个角色的编制、模型/effort、派活模板、降级路径 |
| `../.dsh/skills/` | 7 个 project-local DSH skills（角色技能） |
| `../tools/validate_framework.py` | 引用完整性/覆盖/可达性校验（0 token） |

## 核心决策

| 决策 | 选择 |
|---|---|
| 控制面 | Kernel（Host plugin）+ Lead；Kernel 唯一状态写者 |
| 主链 | INIT→INTAKE→MODELING→METHOD→METHOD_GATE→FIGURES→MODEL_REVIEW→WRITING→DRAFT_REVIEW→REVIEW⇄FIX→COMPLIANCE→DELIVER |
| 人工门 | G0/G2/G3/G5 必过；G1/G4 例外；典型 4 次交互 |
| 角色形态 | Lead + Writer 持久；Solver/Method/Figures/Reviewer 一次性 specialist |
| 返工生命周期 | 局部修复 resume 同一 child；根因返工 fresh + 失败档案 + 重做计划门 + 回归测试；同一 failure_mode 重复 → G1/G4 |
| 模型 | 当前统一 `deepseek-flash`（V4.1-Flash）；按角色调 effort；新模型只改 `framework.json` + 同题 A/B |
| 产物 | 沿用现有路径；`framework.json.artifacts` 为唯一注册源 |
| 机查 | 现有 Python 脚本不改判据；Kernel 包装并记录证据 |
| 降级 | Kernel 故障时退回 `AGENTS.md` 手工协议 |

## 验证

```powershell
# 在仓库根运行
$py = ".venv\Scripts\python.exe"
& $py tools\validate_framework.py
```

验收：退出码 0，0 ERROR；输出 stages/gates/roles/artifacts/checks 数量与覆盖摘要。
Phase 0 验收还要求：迁移矩阵覆盖 100%、8 个 tabletop 与 `framework.json` 一致、用户评审通过。

## 当前状态与下一步

- **Phase 0（已完成）**：框架文档 + 规格 + schema + 机查清单 + 迁移矩阵 + tabletop + validator。
- **Phase 1（Kernel CLI 已完成）**：`tools/pipeline_kernel.py` 实现状态、机查、门、预算、freshness、failure dossier、计划门、回归测试、T55 返工路由；`tools/test_pipeline_kernel.py` 11 项测试全部通过（含真实 INTAKE 机查）。
- **Phase 1 DSH 插件（已启用/active）**：`plugin/modeling-pipeline/` 经隔离 profile 与 `parameters` 标准 JSON Schema 修复后已启用；`plugin_manager` 显示 `fiberPhase: active`，`Tool.listTools` 可见 6 个工具（`pipeline_status` / `start` / `submit` / `gate` / `freshness` / `rework`）。两次踩坑记录见 [`lessons/dsh-plugin-lessons.md`](lessons/dsh-plugin-lessons.md)。**协作纪律：同一时间只让一个 AI 改 `index.js`。**
- **Phase 1.5（已完成）**：live 会话调用 `pipeline_status` 成功返回 `run_id=plugin-test-run`、`stage=INTAKE`、`gate=G0`；插件→Python Kernel 闭环。
- **Phase 2A（已完成）**：7 个 project-local DSH skills 在 [`.dsh/skills/`](../.dsh/skills/pipeline-protocol/SKILL.md)；Team 编制与派活模板见 [`system/team/team-blueprint.md`](team/team-blueprint.md)。本阶段不新建 plugin/preset，避免再影响 live profile。
- **Phase 2B（已完成，2024B 交付）**：2024B 全链路跑通并交付：Q1-Q4 全覆盖、10 图、正文 29 页/摘要 1 页、review 94/100 ACCEPT、R1 high 修复、COMPLIANCE 0 ERROR、G5 `DELIVERED`；过程问题与修复见 [`lessons/2024b-run.md`](lessons/2024b-run.md)。
- **Phase 2C（已完成）**：7 个 skill 已自包含；领域知识在 `.dsh/skills/*/references/`（solver 方法卡/惯例、method gate、figure playbook/recipes、writing specs、review checklists）；运行期不再引用 `.trae/agents|papers|skills`，旧角色全文归档在 `system/archive/legacy/`。代码检查器仍走 `.trae/code_templates`（Phase 3 迁 `tools/`）。记录见 [`lessons/skill-distillation.md`](lessons/skill-distillation.md)。
- **Phase 3（只读 MVP，已完成）**：`plugin/pipeline-console` 侧栏 **Pipeline** + 中央面板；run/stage/gate/checks/figures/paper/gate packet。旧 bundle 已停用。
- **Phase 3b（已完成）**：`plugin/pipeline-console-3b` 门决策按钮（approve/fix/rollback/return_*/stop/deliver + reason，走 Kernel `gate`）和图区域反馈（拖矩形 + 评论 → `decision_logs/figure_feedback.json`）。
- **Phase 3c（已完成）**：`plugin/pipeline-console-3c` 已安装：图 overlay 编辑器（新增/选中/拖动/删除文字框、改内容/字号/颜色/背景、空白处加字、保存 `figure_annotations.json`、导出 `*.annotated.png/.pdf`）。Host API `/annotations`、`/annotations/export` 已验证；旧 3b 已停用。记录见 [`lessons/figure-editor-design.md`](lessons/figure-editor-design.md)。
- **Phase 4**：校准-A/B + 调预算 + 赛前冻结。

### Phase 1 用法（CLI，当前稳定接口）

```powershell
$py = ".venv\Scripts\python.exe"
& $py tools\pipeline_kernel.py start --project-root runs\<run-id> --track opt --profile balanced --contest-profile cumcm
& $py tools\pipeline_kernel.py status --project-root runs\<run-id> --view brief
& $py tools\pipeline_kernel.py submit --project-root runs\<run-id> --stage MODELING --role solver --produced-by solver
& $py tools\pipeline_kernel.py gate --project-root runs\<run-id> --gate G2 --decision approve --reason "..."
& $py tools\pipeline_kernel.py freshness --project-root runs\<run-id> --role solver --trigger local_fix --scope local
& $py tools\pipeline_kernel.py validate-rework-plan --project-root runs\<run-id>
& $py tools\pipeline_kernel.py run-regressions --project-root runs\<run-id>
& $py tools\pipeline_kernel.py route --project-root runs\<run-id>
```

测试：

```powershell
$env:PYTHONPATH = (Resolve-Path tools).Path
$env:RUN_KERNEL_INTEGRATION = "1"   # 可选：跑真实 INTAKE 机查
& $py -m unittest tools.test_pipeline_kernel -v
```

`submit --no-checks` 只用于测试，**不得在真实运行中使用**。

## 旧图说明

根目录 [系统框架图.png](../系统框架图.png) 是 v2 协作流程图，保留为 legacy 参照；v3 的架构图与状态图见 `framework.md` §3/§4。Phase 0 不复制、不覆盖该图。

## 一条纪律

**先改规格，再改提示词。** 新增/修改规则先进 `framework.json`、skills 或 checks，再同步 skill/prompt；禁止只改提示词而不登记。
