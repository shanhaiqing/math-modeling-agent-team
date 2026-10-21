# 数模专家团 · 基于 DeepSeek Harness 的多智能体建模流水线

面向数学建模竞赛的一体化多智能体系统：把「读题 → 建模 → 求解 → 出图 → 写作 → 评审 → 交付」拆成显式状态机、文件契约和 6 道人机门，由 9 个 Agent 角色协作完成。

## 架构

```text
Lead / 人机门
  ├── Kernel：pipeline_kernel.py（唯一状态写者）
  │     ├── 20 阶段 / 55 转移 / 6 门 / 9 角色
  │     ├── 47 个产物契约 / 35 条机查 / 7 个 Schema
  │     └── 返工：failure_dossier → rework_plan 计划门 → 回归 → T55 下游路由
  ├── DSH Host 插件：6 个 pipeline_* 工具
  ├── 7 个 project-local skills：solver-opt/stats、method-critic、figure-studio、
  │   paper-writer、independent-reviewer、pipeline-protocol
  └── Pipeline Console：run/门/机查/图/论文/成本；门决策、图区域反馈、overlay 文字编辑
```

## 关键能力

- **确定性控制面**：阶段、门、产物 hash、机查和返工由 Python Kernel 统一管理，不依赖模型记忆。
- **人机门**：G0–G5；门没到、机查未过不能放行；独立评审不读作者推理日志。
- **失败不重复**：`fresh_dossier` 走失败档案、重做计划门和回归测试；`resume` 只改局部。
- **角色自包含**：7 个 `SKILL.md` + `references/`；运行期不依赖旧 Trae 角色长文。
- **图可反馈/可修正**：区域反馈写入 `figure_feedback.json`；overlay 编辑器保存 `figure_annotations.json`，导出 `.annotated.png/.pdf`，原图不变。
- **真实链路验证**：2024 高教社杯 B 题全流程交付；正文 29 页/摘要 1 页、10 图、独立评审 94/100 ACCEPT、COMPLIANCE 0 ERROR、G5 DELIVERED。

## 快速开始

```powershell
# 1) 框架自检
.venv\Scripts\python.exe tools\validate_framework.py

# 2) Kernel 测试
$env:PYTHONPATH = (Resolve-Path tools).Path
.venv\Scripts\python.exe -m unittest tools.test_pipeline_kernel -v

# 3) 新建一局（示例）
.venv\Scripts\python.exe tools\pipeline_kernel.py start `
  --project-root runs\demo --track opt --profile balanced --contest-profile cumcm
.venv\Scripts\python.exe tools\pipeline_kernel.py status `
  --project-root runs\demo --view brief
```

在 DSH 中安装 Host 插件与 Console：

```text
plugin_manager action=install_bundle target=<repo>/plugin/modeling-pipeline
plugin_manager action=install_bundle target=<repo>/plugin/pipeline-console-3c
```

## 目录

| 路径 | 内容 |
|---|---|
| `system/` | v3 框架、机器规格、checks、schema、门卡、迁移矩阵、tabletop、经验 |
| `tools/` | `pipeline_kernel.py`、测试、框架自检、`annotate_figure.py` |
| `tools/checks/` | 机查脚本、LaTeX/论文模板、求解模板、轨道映射 |
| `plugin/` | DSH Host 插件与当前 Pipeline Console |
| `.dsh/skills/` | 7 个自包含角色技能（含 references） |
| `runs/` | 本地运行产物（不提交；含论文/图/提交包） |
| `legacy-trae-archive`（分支） | 旧 Trae 资产与旧控制台，仅追溯用 |

## 状态与路线

- **已完成**：Phase 0 框架 → Phase 1 Kernel → Phase 1.5 DSH 插件 → Phase 2A skills/Team → Phase 2B 2024B 全链路 → Phase 2C 技能自包含 → Phase 3/3b/3c 控制台、门决策、图反馈与 overlay 编辑。
- **下一步**：Phase 4 校准/A-B、质量/成本基线与赛前冻结。
- **兼容性**：Kernel 是平台无关的 Python + 文件状态；DSH 是当前适配层。旧 Trae 资产已归档到 `legacy-trae-archive` 分支，`main` 只保留运行所需资产。

## 说明

- 本仓库不包含测试赛题 PDF、`runs/`、论文/提交包等运行产物。
- 图 overlay 编辑是“注释层”方案，不直接修改原图 PDF 的文字对象。
