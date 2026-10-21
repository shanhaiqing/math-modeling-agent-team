# 数模 B 题智能体流水线（v3）

本文件是工作区守则。**权威规格**：

- 人读框架：[`system/framework.md`](system/framework.md)
- 机器规格：[`system/framework.json`](system/framework.json)
- 机查定义：[`system/checks.json`](system/checks.json)
- 门卡：[`system/gates/`](system/gates/)
- Team 编制：[`system/team/team-blueprint.md`](system/team/team-blueprint.md)

旧 Trae 资产已归档到 `legacy-trae-archive` 分支；当前 `main` 不再保留 `.trae/`。

## 运行方式

1. **Lead 只通过工具推进**：`pipeline_status/start/submit/gate/freshness/rework`；不要手改 `run_state.json`、`pipeline_state.json` 或 `events.jsonl`。
2. **6 道人机门 G0–G5**：门没到、机查未过不得放行；不得跳过用户确认自动推进。
3. **Agent 技能**：`.dsh/skills/<role>/SKILL.md + references/`；角色只读自己的技能与 handoff 清单。
4. **Kernel**：`tools/pipeline_kernel.py` 是唯一状态写者；机查脚本在 `tools/checks/`。
5. **运行产物**：写入 `runs/<run_id>/`，不提交 Git；`runs/` 已在 `.gitignore`。
6. **图编辑**：区域反馈写 `figure_feedback.json`；overlay 编辑写 `figure_annotations.json`，导出 `*.annotated.*`，不改原图。

## 启动确认

启动前确认四件事：

- 项目根路径
- `problem_track`：`opt` / `stats`（无缺省）
- 赛制剖面：`cumcm` / `shuwei_zh` / `shuwei_en`
- 题面是否齐备：`赛题/题面.md`

## 质量与返工

- 产物契约、机查、独立评审、COMPLIANCE 按 `system/framework.md`。
- 返工走 `failure_dossier → rework_plan 计划门 → 回归测试 → T55 下游路由`；不得跳步。
- 独立评审不读作者推理日志；图中白名单 PNG 才可读。

## 禁止

- 手改状态文件或伪造门决策。
- 跳过用户门/机查自动推进。
- 把同题专有信息写入共享文件或技能 references。
- 提交 `runs/`、测试赛题、`.venv/`、生成报告到 Git。
- 用 `.trae` 旧路径作为运行期依赖；旧资产只在 `legacy-trae-archive` 分支查阅。
