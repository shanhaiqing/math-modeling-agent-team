# C 系统补强方案（基于两系统差距报告，2026-08-31）

> 状态：✅ 已批准并全部执行完毕 ｜ 落地 commit：
> - P0：`11ee66d` + 追加压缩 `802207c`
> - P1：`8a5e8cf`
> - P2：`4265861`
> - P3-A：`9f38e9e`
> 依据：[两系统差距报告.md]（同目录）
> 原则：只移植**题型无关的通用资产**（零冲突项）；C 的定位性差异（优化求解器六件套）不移植；每条附风险与适配点。

---

## P0 — 修复 agent 可用性缺陷（悬空引用 + 机制冲突）

**事实**（已 grep 核实）：
- `rules/c题流水线.md` 被 4 个 agent 文件引用 4+ 处（实际不存在，rules/ 仅 orchestrator.md）
- 旧名"红队配额机制"出现 8+ 处，且 agent 文件仍含"至少找出 3 个 high severity 问题"的**旧配额制表述**，与 C 系统 AGENTS.md 现行"红队自查机制（努力举证制，不设配额、禁止凑数）"**实质冲突**

| 改动 | 内容 | 来源 |
|------|------|------|
| P0-1 | 4 个 agent 文件中 `rules/c题流水线.md` 引用全部重定向：红队机制引用 → `AGENTS.md`"红队自查机制"节；handoff 契约九字段引用 → `AGENTS.md`"handoff 契约"节 | 修复悬空 |
| P0-2 | "红队配额机制"旧名与"至少找出 3 个 high severity"配额表述 → 统一改为"红队自查机制（努力举证制）"表述，与 AGENTS.md 对齐 | 修复机制冲突 |

风险：低（纯引用与术语对齐，不含新机制）。优先级：P0 最高——社会主义 agent 接到 spawn 会找不存在的文件。

## P1 — 通用机查与编排协议移植（从 B 直接平移）

### P1-A：9 个机查脚本移植

| 脚本 | 移植适配点 |
|------|-----------|
| `check_code_hygiene.py` | 黑名单词表按 C 语境适配（HG0/反思门/红队/机查等词两系统通用，基本零改动） |
| `check_workspace_hygiene.py` | 零改动 |
| `check_latex_env.py` | 零改动（含编译降级机制） |
| `check_latex_compliance.py` | C 已有（不移植，保持 C 版） |
| `check_abstract_guard.py` | 零改动 |
| `check_tex_numbers.py` | 输入引用改为 check_solution_json_c 的字段口径 |
| `check_viz_tests.py` | 零改动（C 已有 3 个 test_*，补执行器即可） |
| `check_convention_refs.py` | 惯例路径改为 C 的《国赛公开惯例.md》《数据题专项惯例.md》 |
| `check_card_refs.py` | 卡片路径改为 C 的"数据方法卡片/" |

### P1-B：orchestrator.md 补三项协议 + 机查表

- 补 **断点接管协议**（§3，从 B 平移）
- 补 **subagent 上下文接力协议**（§3，含 `subagent_ids` 字段）
- 补 **隔离审计签名规程**（§8 + §3 增 `isolation_signatures` 字段——C 现调用 check_isolation 不带 --signature，签名缺失 = 审计无效）
- §4 机查表从 5 行补齐（WRITING 预检行 / COMPLIANCE 打包行 / 任意转换工作区卫生行 / 绘图回归行 / 惯例引用行）

风险：低-中（纯平移 + 少量路径适配）。

## P2 — 打包、卫生契约与技能

| 改动 | 内容 |
|------|------|
| P2-1 | 移植 `package_support_materials.py`（终扫黑名单按 C 语境） |
| P2-2 | C 系统 AGENTS.md 补"支撑材料卫生契约"+"工作区卫生契约"两条（从 B 平移） |
| P2-3 | 复制 figure-studio / reference-studio 两个技能到 C 的 `.trae/skills/`（零改动）；摘要写作规范、去AI味规范从 B 惯例中独立成 C 版文件（按 C 语境微调示例） |

风险：低。

## P3 — 版本管理落地（防过拟合铁律 6 的前提）

C 系统无独立 git 仓库、无根 .gitignore。**物理事实：C 系统目录位于 B 仓库根之内**（`数模C题专家团/` 当前为未跟踪状态）。

| 选项 | 方案 |
|------|------|
| P3-A（推荐） | 将 C 系统共享文件（`.trae/`、`AGENTS.md`、`requirements.txt`）纳入 B 仓库版本管理，补齐根级 .gitignore；C 的起跑产物（比赛赛题/ 等）保持忽略 |
| P3-B | 在 C 根建独立 git 仓库 |

推荐 P3-A：零额外基建，铁律 6（commit 绑定落地）在两系统共用同一执行通道。

## 可选批次 — B 反向吸收 C 独有优势

- OB-1：`plot_line/bar/scatter/heatmap/tornado/convergence` 便捷封装回流 B 的 visualization_style.py（附 4 测试回归）
- OB-2：`stage5_review.json 禁读`条款回流 B（reviewer prompt + AGENTS.md 信息隔离节）
- OB-3：B requirements.txt 补 `ortools`/`networkx`/`scikit-learn`/`statsmodels` 锁版本（修复 D2 缺口）

## 执行与审批机制

- 审批通过后按 **P0 → P1 → P2 → P3** 顺序执行，每批完成即用相应机查自检（移植后的 check_* 首次运行视为验收）
- 落地遵循铁律 6：逐字写入 → 回读核对 → git commit（message 含批次号 `[2026-08-C补强-Pn]`）→ 哈希写入本文件