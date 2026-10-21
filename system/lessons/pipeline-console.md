# Phase 3：Pipeline Console（只读 MVP）

## 目标

把“状态在聊天/JSON 里”变成 Web UI 里可点的仪表盘：侧栏一个 **Pipeline** 图标，中央面板看 run、阶段、门、机查、返工、评审、图、论文、门包。

## 交付

- Bundle：`plugin/pipeline-console/`
- 侧栏：`sidebar.panellist` id `pipeline`，order 20
- 中央：`main` key `pipeline`
- Host 路由（同源，GET）：
  - `/pipeline-console/runs`
  - `/pipeline-console/detail?run=<id>`
  - `/pipeline-console/file?run=<id>&path=<relative>`
- 文件读取限制在 run root 内，路径穿越被拒绝；只读，无写操作。
- 安装：`plugin_manager install_bundle` → `application: applied`；bundle `@local/pipeline-console` 已启用。

## 为什么先做只读

- 先验证 Host 数据面、slot 注册、主题/布局和文件读取；
- 门决策的写操作涉及 Kernel gate/权限/人工确认，下一版单独做；
- 只读 UI 即使有渲染问题，也不会改流水线状态。

## 已验证

- `plugin_manager install_bundle` 返回 `application: applied`，无 warnings；
- Client `Slots.listSubTree`：
  - `main` occupants 含 `pipeline`（active）
  - `sidebar.panellist` occupants 含 `pipeline`（order 20，active）
- Host API：
  - `/pipeline-console/runs` 返回 `b-test-01`（DELIVERED）与 `plugin-test-run`（INTAKE/G0）；
  - `/pipeline-console/detail?run=b-test-01` 返回 stage/status/checks/figures=10/files=6/decisions=8；
  - `/pipeline-console/detail?run=plugin-test-run` 返回 `gate=G0` + options `approve,fix,stop`；
  - `/pipeline-console/file?...fig01_q1_oc.png` 200 image/png 156141B；`paper.pdf` 200 application/pdf 830367B。

## 未验证 / 下一步

- **视觉渲染未验证**：没有浏览器控制；slot active + Host API 200 不等于“用户看到的面板完全正确”。需要打开 Web UI 侧栏 **Pipeline** 目视检查（刷新页面后再看）。
- 下一版写操作：
  - Gate 按钮（approve / rollback / return_figures / return_writing / stop）+ reason；
  - 写操作必须经 `pipeline_gate` 同一路径，不能直接写 `run_state.json`；
  - 需要权限/确认与错误回显。
- 成本/token 面板、历史 run 对比、artifact diff 可后续加。

## 安装与回退

- 安装前 profile 备份：`C:\Users\35399\.dsh\backups\pipeline-console-20261021-150540`
- 若 UI 异常：`plugin_manager set_bundle target=@local/pipeline-console enabled=false`，或从 Plugins 页停用；不影响 Kernel/CLI。

## Phase 3b 更新（当前）

- 新 bundle：`@local/pipeline-console-3b`（`plugin/pipeline-console-3b/`，0.2.0）；旧 `@local/pipeline-console` 已停用。
- 新增 Host POST：
  - `/pipeline-console/gate`：调用 Kernel `gate`，支持 approve/fix/rollback/return_*/stop/deliver；reason 必填；scope/root_cause 可选。
  - `/pipeline-console/figure-feedback`：拖矩形 + 评论，写 `decision_logs/figure_feedback.json`。
- 已验证：
  - `console-gate-test` 的 G0 经 console POST approve → stage `MODELING`；
  - `b-test-01` 的 fig01 反馈 POST → `figure_feedback.json` 写入。
- 仍是 **区域反馈**，不是直接拖字/改字；直接编辑见 [`figure-editor-design.md`](figure-editor-design.md)。
- 视觉渲染（按钮/弹窗/拖拽）仍需浏览器目视确认；Host API 与 slot 注册只能证明数据面。

## Phase 3c 更新（当前）

- 新 bundle：`@local/pipeline-console-3c`（`plugin/pipeline-console-3c/`，0.3.0）；旧 3b 停用；侧栏/主面板 id 仍是 `pipeline`。
- 图卡片新增 **Edit image**：overlay 编辑器，支持新增/选中/拖动/删除文字框，改文本/字号/颜色/背景，空白处加字，保存与导出。
- Host API：
  - `GET|POST /pipeline-console/annotations`
  - `POST /pipeline-console/annotations/export`
- 数据/导出：`decision_logs/figure_annotations.json`；`tools/annotate_figure.py` 生成 `*.annotated.png/.pdf`，原图不变。
- 已验证：GET/POST/export 通过；annotated PNG/PDF 生成；拖拽/像素对齐需浏览器确认。

