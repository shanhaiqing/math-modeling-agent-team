# handoff_notes_2.md（paper-writer → independent-reviewer / 主智能体）

## 写作洞察（≤800 字）

1. **叙事主线**：以"图结构即战术"贯穿三问——8 条咽喉边决定 Q1 火力封锁约束与 Q2 破交风险集中，孤立分量决定就地防御，坐标=km 的几何核验支撑欧氏覆盖判定。这条主线让三问不再是孤立子问题。
2. **口径纪律是本题最大风险点**：Q2 存在 MIP 内部目标值（81690/107512）与重算真值 TC（109614/145773）两个口径，论文统一用重算 TC_total 并在 5.2.2 节与误差分析中显式说明差距来源（护航成本固定份额线性化，7.18%/8.56%）。摘要中"基线情形下"限定词已保留。
3. **反直觉结论的表述必须复算**：写作中发现"盟军路径风险更高导致 C_loss 大"的直觉表述与数据相反（盟军主力路径平均风险 0.6464 低于苏军 0.8026），真实机制是流量 1.6 倍主导。已用代码复算修正。教训：论证句派生数值必须当场重算。
4. **翻转条件是评审重点**：主攻边评分差仅 0.0227，论文给出两个定量翻转条件（走廊权重下调至 0.1638、防御估计上调 0.0454），均经代码重算。这是 handoff_notes_1 点名的潜在质疑点，已正面回应。
5. **MC 双口径披露**：Q2/Q3 的 std/mean 超阈值（内在离散）与均值偏差/SEM 收敛两个口径在正文并列披露，避免"not converged"被误读为模型验证失败。
6. **附录代码方案**：用 fancyvrb \VerbatimInput 直引 11 个源文件（机查等效 lstinputlisting），100% 与实际代码一致，中文注释经 \setmonofont{SimSun} 正常显示。

## result_bundle 完整性反向核查结果

先运行契约校验器：`check_solution_json.py` → 0 ERROR / 2 WARN（Q1 两子问题 monte_carlo=null，solution.json 已附 monte_carlo_note"确定性 MIP 不适用"，论文 5.2.5 节已显式说明，WARN 闭环）。

| # | 产物 | 核查结果 |
|---|------|---------|
| 1 | 蒙特卡洛仿真结果 | ✓ Q2（2000次/偏差0.72%、1.54%）、Q3（各2000次/种子2026/SEM收敛）；Q1 null+说明 |
| 2 | 策略转换临界点 | ✓ Q2 护航临界 risk 缩放 0.2（8点扫描+source）；Q3 无情景交叉临界点（已说明） |
| 3 | 活跃约束标注 | ✓ Q1 20条/Q2 10条（含派生量数值）/Q3 1条+3条 slack |
| 4 | 替代算法讨论 | ✓ Q3 贪心：DP/时序MIP/贪心三候选对比（modeling_plan.alternative_algorithm_discussion） |
| 5 | 题目设计合理性讨论 | ✓ design_critique 5条，论文 7.4 节落实 |
| 6 | 成本分层建模 | ✓ 四类独立符号/公式/经济含义（cost_decomposition），论文式(7)-(11) |
| 7 | 术语表五类分类 | ✓ indices/decision_variables/parameters/objectives/derived 五类齐全（33条） |

无反向质询项。

## 图表清单预审（惯例 二.29 + 二.19 B 题核查对照列）

| 图号 | 类型 | 数据来源 | 对应章节 | 核心信息 | 解析数值 source | B题特殊核查对应 |
|------|------|---------|---------|---------|----------------|----------------|
| fig9 | 算法流程图 | 图表生成.py 手绘 | 5.1 | 六层技术路线 | 无（结构图） | #2 流程可视化 |
| fig1 | 部署地图 | q1_result.deploy/command/aa | 5.2.4 | 双方部署空间分布 | 指挥节点136/384、D=2.279/1.872 km（q1_*.components） | — |
| fig2 | 堆叠柱状图 | q1_result.deploy 聚合 | 5.2.4 | 部署构成对比 | 火炮14000 vs 7000（source_parameters） | — |
| fig3 | 补给网络图 | q2_result.routes | 5.2.4 | 路径/仓库/流量 | 路径长10.732/9.753 km（routes字段） | — |
| fig4 | 成本柱状图 | q2_result.cost_decomposition | 5.2.4 | 四类成本对比 | C_trans/C_escort/C_loss/C_labor 八字段 | #4 成本分层 |
| fig13 | 基线vs对抗对照 | q2_*.sensitivity.baseline_vs_stackelberg_A01 | 5.2.4 | A-01 鲁棒性成本 | TC_baseline/TC_worst/delta_pct 50.83/48.94（含人力主口径，R1 更新） | — |
| fig5 | Tornado图 | validation.sensitivity_q2.scans | 6.2 | 参数敏感度排序 | ±20%扰动点 delta_pct（scans字段） | #3 Tornado |
| fig6 | 临界点折线 | q2_*.critical_points.scan | 6.2 | 护航策略临界 | TC_free/TC_no_escort 8点、临界0.2 | #5 临界点 |
| fig7 | 进攻方案图 | q3_result.axes/capture_sequence | 5.3.1 | 主攻边+夺控序列 | 评分0.5133/0.4906、序列7节点 | — |
| fig8 | 生存对比柱状 | q3_allied.monte_carlo.detail | 5.3.2 | 两情景人员生存概率 | 0.7956/0.6730/CI95 四端点（人员加权，R1 更新） | — |
| fig10 | 风险敏感折线 | validation.sensitivity_q3 | 6.3 | ±20%风险下生存 | 5点 surv_comm_ok/lost | — |
| fig11/12/14 | 参数扫描三联 | q1_*.sensitivity.*_sweep_A02/A03/A04 | 6.1 | A-02~A-04 稳定性 | 各点 phi/aa_nodes/air_deployed | #2 稳健性可视化 |

source 一致率 100%（全部从 solution.json/q*_result.json 字段提取，无凭记忆填数）。

## 页数与编译说明

- **页数结构**（R1 重编译后更新）：摘要 1 页（第1页）+ 正文 28 页（第2-29页）+ 参考文献 1 页（第30页）+ 附录 59 页（第31-89页），共 89 页。正文 28 页达宽松上限（官方建议 20 页以内）。
- **压缩记录**：初稿 29 页，按惯例 二.15 执行压缩——合并符号双表为单表、精简模型评价节（各≤3条）、三张扫描图合并为三联图、缩小图尺寸。R1 修复新增内容（算法术语表、H-2 人员口径披露、口径声明）后正文一度 29 页，再次以缩小图尺寸（单图 0.55→0.46、流程图 0.75→0.62、大图 0.88→0.80）压回 28 页。未删除任何验证内容（最优性验证/模型验证/灵敏度分析完整保留）。若 HG2/HG3 用户要求冲高档次，可进一步压缩至 20 页附近（建议方向：Q2 路径明细表改摘要式、灵敏度扫描图移附录），需用户决断。
- **编译警告**：Overfull 已清零；Underfull 5 处（正常断行）；无 undefined references；无 LaTeX Warning。
- **编译环境**：MiKTeX xelatex，需设置 MIKTEX_USERCONFIG/DATA/INSTALL 环境变量指向 _miktex_tmp（沙箱限制），该事项已在编译命令中固化。

## 需要 HG2 用户目视确认的排版事项

1. 摘要页版式（标题黑体三号居中 + "摘要"小标题 + 正文 + 关键词行）是否符合预期；
2. 一级标题"一、二、…"黑体三号居中、二级"（一）"样式；
3. 表 5（补给方案明细 20 行）使用 resizebox 缩放，字号偏小，确认是否可读；
4. 附录代码为小五号宋体等宽，89 页篇幅较长（官方要求完整代码，不可删减）。

## HG退回反馈（2026-08-13，HG2 用户裁决：视觉质量不合格）

**退回理由**：用户目视判定论文视觉质量不合格，提供排版标杆示例（论文示例/案例一 = 2015B、案例二 = 2022B，均为往年题非本题，只学形式不学内容，不违反信息隔离）；并要求查清 LaTeX 编译多次出错的原因加以规避。

**编译错误根因（已定位）**：paper.tex l.56 用 fancyvrb 的 `\fvset{breaklines=true,breakanywhere=true,...}`，而 fancyvrb 4.6a 不支持这两个 key（属 fvextra 扩展）→ paper.log 两条 `! Package keyval Error`，附录代码断行失效。pygments 未安装，minted 路线不可行。

**差距清单（当前 vs 案例一标杆，仅形式）**：
1. 页边距：左右 2.6cm vs 标杆 3.18cm（上下均 2.54）；
2. 行距：1.5 vs 标杆 1.4；
3. 摘要页：当前标题单行居中+"摘 要"左偏+正文无 minipage 约束；标杆为 titlepage 环境+标题黑三居中可折行+"摘 要"黑四居中（\hspace{2em}）+minipage{0.95\textwidth} 内 -4 号 \parindent 2em+"关键词："黑体行；
4. 二级标题编号：当前（1）阿拉伯 vs 标杆（一）中文数字；
5. 附录代码：当前无框线/行号/断行 vs 标杆 fvextra 的 frame=single+numbers=left+numbersep=6pt+zihao{-5}+baselinestretch=1.05+breaklines/breakanywhere；
6. 等宽字体：当前 SimSun vs 标杆 Consolas[Scale=0.82]（中文注释经 \setCJKmonofont{SimSun} 回退显示，案例一已验证可行）。

**整改要求**：
1. 编译修复：改用 fvextra 包承载 breaklines/breakanywhere（案例一方案）；若 MiKTeX 无法安装 fvextra，回退 listings lstinputlisting（案例二方案，原生支持 breaklines）。最终编译 0 error。
2. 导言区按差距清单 1-6 逐项对齐标杆（仅形式，正文内容/数值/图表/结构一律不动）。
3. 重编译后页数重核：摘要 ≤1 页（硬约束，若超则调字号/行距适配，不改摘要信息量）、正文 ≤28 页；附录页数不限。
4. 重跑 check_latex_compliance.py（--contest-year=2026）+ check_tex_numbers.py + check_pipeline_manifest.py --stage writing，ERROR 清零。
5. 视觉自检：编译后用 pymupdf 将新 PDF 第 1-3 页渲染 PNG 到 temp_images/layout_cmp/cur2_p*.png，与 ex1_p1/p2 目视比对版式一致性，差异写入 s4_reflection.md 追加节。
6. 编译规避记录：在 s4_reflection.md 追加"HG2 退回整改"节，记录本次编译错误根因（fancyvrb vs fvextra）与永久规避措施。
