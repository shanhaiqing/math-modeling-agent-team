# 优化问题分类决策树（B 题）

> v1.3 (2026-09-08)：modeling-solver 阶段 1 初判 + 阶段 2 GQ3 后复核。主输出为数学模型类 `problem_type`；多目标/图/组合/排队/博弈/可 DP 化为 `overlays` 叠加，**不得覆盖**主类型（DP / 纯网络除外，见 Q2b / Q5 纯网络检验）。

---

## 决策树

```
开始
  │
  ▼
Q1: 目标数量？
  ├── 多目标（≥2 个冲突目标）──────→ overlays += MOO，续 Q2
  │     （有主次 /「首先保证 A」时，主类型仍按主目标走规划类）
  └── 单目标 ─────────────────────→ Q2
      │
      ▼
Q2: 是否存在时间维度（多阶段决策且阶段间有递推关系）？
  ├── 是 ──→ time_dependence = multi_period，续 Q2b
  └── 否 ──→ time_dependence = static（或 continuous_time 若连续时间），续 Q3
      │
      ▼
Q2b: 以下三条是否同时成立？
     ① 能写出低维状态 s_t，并估计 N×S×D 在可填表范围（约 10^8）
     ② 无后效（未来只通过 s_t 耦合）
     ③ 不是「线性平衡 + 容量 + 整数链接」更能写成 MIP 的结构
        （生产 / 库存 / 多周期产能 / 检测次数等）
  ├── 三条皆是 ──────────────────→ problem_type = DP，可结束
  └── 任一为否 ──────────────────→ overlays += DP_candidate（可选对照），续 Q3
      │
      ▼
Q3: 决策变量是否包含离散/整数变量？（含线性化将引入的整数辅助变量）
  ├── 否（全部连续）──────────────→ Q4
  └── 是（含 0-1/整数/混合）─────→ Q5
      │
      ▼
Q4: 目标函数和约束是否全部线性？
  ├── 是 ────────────────────────→ problem_type = LP
  └── 否（含非线性）──────────────→ Q4L
      │
      ▼
  Q4L: 非线性项能否在可接受等价/松弛下线性化？
      （0-1×连续、分段线性、固定费用、可化线性的分式）
    ├── 是 ──→ linearized = true，按 MIP 进入 Q5 链
    └── 否 ──→ Q4a
      │
      ▼
  Q4a: 目标函数是否可微？可行域是否凸？
    ├── 是（凸优化）──────────────→ problem_type = NLP（objective_type = nonlinear_convex）
    └── 否（非凸）───────────────→ problem_type = NLP（objective_type = nonlinear_nonconvex）
      │
      ▼
Q5: 问题是否具有网络/图结构？
  ├── 是 ──→ overlays += Network
  │     若模型只有流守恒 + 容量、无选址/指派/额外 0-1
  │       → 允许 problem_type = Network
  │     否则续 Q5a（主类型仍走 IP/MIP）
  └── 否 ──→ Q5a
      │
      ▼
  Q5a: 组合结构是否显著（排列/子集选择/匹配）？
    ├── 是 ──→ overlays += Combinatorial，续 Q5b
    │     （主类型仍为 IP/MIP，除非书面说明专用组合算法优于通用 MIP 的规模/结构理由）
    └── 否 ──→ Q5b
        │
        ▼
    Q5b: 变量是全整数还是混合？
      ├── 全整数 ────────────────→ problem_type = IP
      └── 混合整数 ──────────────→ problem_type = MIP
```

---

## 各类型特征速查

| 类型 | 含义 | 变量 | 目标/约束 | 典型求解 |
|------|------|------|-----------|----------|
| LP | 主类型 | 连续 | 线性 | 单纯形、内点 |
| IP | 主类型 | 整数 | 线性（或已线性化） | 分支定界 |
| MIP | 主类型 | 混合 | 线性（或已线性化） | 分支定界 |
| NLP | 主类型 | 连续 | 不可线性化的非线性 | 多起点局部搜索 |
| DP | 主类型（仅 Q2b 三条皆是） | 阶段状态 | 可加递推 | 填表递推 |
| Network | 主类型（仅纯网络）或 overlay | 流 | 流守恒+容量 | 网络单纯形 / MIP 辅 |
| MOO / Combinatorial / Queueing / Game / DP_candidate | **仅 overlay** | — | — | 见对应卡片；不得写进 problem_type 覆盖规划类 |

---

## 边界情况处理

| 情况 | 处理 |
|------|------|
| 含随机参数 | 主类型不变，`uncertainty = stochastic`（如 MIP + stochastic） |
| 含不确定参数且需鲁棒解 | 主类型不变，`uncertainty = robust` |
| 排队论特征 | **overlays += Queueing**，主类型仍由 Q3–Q5 给出 |
| 博弈/竞价特征 | **overlays += Game**，主类型仍由 Q3–Q5 给出 |
| 无法明确归类 | problem_type = Other，走第一性原理建模 |

禁止用 Queueing / Game / MOO / Combinatorial 作为 `problem_type` 的唯一取值来替换 LP/IP/MIP/NLP。

---

## 输出映射表（决策树输出 → feature_fingerprint 字段）

> 主类型与叠加分离。历史指纹若仍把 MOO/Queueing/Game/Combinatorial 写入 `problem_type`，复核时改为主类型规划类 + overlays。

| 决策树输出 | problem_type | 其他 fingerprint 字段 |
|---|---|---|
| LP / IP / MIP / DP / Network / Other | 同左 | — |
| NLP_Convex / NLP_Nonconvex | NLP | objective_type = nonlinear_convex / nonlinear_nonconvex |
| Q4L 为是 | MIP 或 IP（由 Q5b） | linearized = true |
| 多目标（Q1） | 不变 | overlays 含 MOO |
| 多阶段但 Q2b 未过 | 由 Q3–Q5 | time_dependence = multi_period；overlays 可含 DP_candidate |
| 含随机参数 | 不变 | uncertainty = stochastic |
| 含鲁棒需求 | 不变 | uncertainty = robust |
| 排队 / 博弈 | 不变 | overlays 含 Queueing / Game |
| 图结构但非纯网络 | 由 Q5b | overlays 含 Network |
| 组合结构显著 | 由 Q5b | overlays 含 Combinatorial |

---

## 使用示例

**例 A（Q2 否支，对照）**

```
题目：从 n 个候选点中选 p 个设施，使总运输成本最小

Q1: 多目标？→ 否
Q2: 多阶段递推？→ 否
Q3: 含离散变量？→ 是（y_j ∈ {0,1}）
Q5: 纯网络（仅流守恒+容量）？→ 否（有选址 0-1）→ overlays 不含 Network 或仅作辅
Q5a: 组合显著且不用通用 MIP？→ 否
Q5b: 混合（选址整数，分配可连续）

→ problem_type: MIP
→ 经典模式：模式 05（选址）
```

**例 B（旧 Q2 会误判、本版必须进 MIP）**

```
题目：T 个周期订货，订货量非负连续、是否订货为 0-1，库存平衡 + 产能上限，最小化订货/持有/缺货成本

Q1: 多目标？→ 否
Q2: 多阶段递推？→ 是 → time_dependence = multi_period
Q2b: ① 状态可写 I_t 但产能 0-1 与多产品耦合后 N×S×D 易爆
     ③ 线性平衡 + 容量 + 整数链接 → 更能写成 MIP
     → Q2b 否 → overlays += DP_candidate（可作对照，不得当主类型）
Q3: 含整数？→ 是
Q5: 纯网络？→ 否
Q5b: 混合

→ problem_type: MIP
→ 经典模式：模式 04（库存）；求解默认 MIP，DP 仅对照
```
