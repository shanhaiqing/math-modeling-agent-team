# fix_round1.md（paper-writer，R1 修复回路日志）

轮次：R1｜日期：2026-08-14｜输入：review_report.json（初审 high 2/medium 4/low 6）+ modeling-solver BLOCKED 回退修复后的数值真源（solution.json 已更新）

## 处置统计

fixed 10 条（H-1、H-2、M-摘要传播、M-贪心承诺、M-术语表论文侧、L-符号、L-假设4、L-图口径、L-舍入、L-MC次数）；rejected 2 条（M-k_def 无对照、M-术语表.json 本体、L-solver_backend 路径——其中术语表条目拆为论文侧 fixed + JSON 侧 rejected，合计 rejected 3 个处置项，对应工单 2 条半）。按工单计：12 条工单 = fixed 10 + rejected 2。另含全节数值重核发现的 2 处连带漂移修复（Q2 求解时间、优势节时间表述）。

## 逐条处置

### H-1 Stackelberg TC_worst 口径混用 —— fixed
- 处置：全文旧值 31.13%/29.59%（及 TC_worst 143734.7/188914.0、绝对增量 34121.0/43141.0）替换为含人力主口径新值 50.83%/48.94%（TC_worst 165334.7/217114.0、绝对增量 55721.0/71341.0），每处均声明"含人力 TC_total 主口径"；不含人力参照口径 +63.31%/+60.68% 以 footnote 一句话披露（5.2.4 节 Stackelberg 段）。
- 修复位置：摘要（paper.tex 问题二段）、表2 A-01 行、5.2.4 节 Stackelberg 最坏情形段与图 fig13 解析段、6.4 节误差来源（2）。
- 数值 source：solution.json q2_soviet/q2_allied.stackelberg_worst_case（TC_worst/delta_pct/extra_loss/delta_pct_excl_labor_reference）与 q2_*.sensitivity.baseline_vs_stackelberg_A01，逐项一致。

### H-2 Q3 转移混合量纲与容量断言 —— fixed
- 处置：全文旧值 0.7548/0.6276/0.1272 替换为人员加权新值 0.7956/0.6730/0.1226；删除"容量约束全部紧"断言，改为如实报告人员容量占用率 50%（松，三节点裕度 39.2/28.7/32.2 万人）+装备随建制伴随口径说明；生存概率语义显式声明"人员加权（人员生存概率）"，覆盖摘要、正文、图 caption 三处。
- 修复位置：摘要（问题三段）、5.3.2 节盟军转移模型（分配公式、分配结果、殿后、路线数、MC 口径、式 surv、图 fig8 解析段全段重写）、fig8/fig10 caption、6.3 节风险敏感性段、6.4 节误差来源（5）、符号表 P_surv 行。
- 数值 source：solution.json q3_allied_withdrawal（objective_value/survival_comm_ok/survival_comm_lost/survival_difference/target_allocation_personnel_万人/personnel_capacity_utilization/active_constraints slack/monte_carlo.detail CI95 与 SEM/std 字段/sensitivity.data 五点），逐项一致。

### M-摘要传播 H-1 数值 —— fixed
- 处置：随 H-1/H-2 同步更新摘要两句；abstract_candidates.md 版 A、版 B 数值同步更新并追加 R1 修复记录行。
- 修复位置：paper.tex 摘要页、decision_logs/abstract_candidates.md。

### M-贪心交叉验证承诺未兑现 —— fixed（表达层）
- 处置：删除"以 MIP 小规模算例交叉验证差距"的承诺性表述，改为诚实披露："建模阶段曾拟以走廊子图小规模 MIP 对照，因时序展开松弛过弱难以给出可靠参照值，该对照未实施，贪心解质量改以蒙特卡洛统计评估（跨步剩余比 std/mean 2.74%<5%）"。未虚构已做对照。
- 修复位置：5.3.1 节算法选择理由第二段。
- 说明：modeling_plan.json 中残留的承诺表述生产者非本 agent，不改（复审可见该 JSON 的 alternative_algorithm_discussion 与论文表述差异时，以论文诚实披露为准）。

### M-k_def 无替代标定对照 —— rejected
- 理由：k_def 数值扰动扫描（×1.5/×2 对照）属建模层补算，超出 R1 修复权限（修复回路铁律：不得改动建模方案与求解数值，发现需补算应走 BLOCKED 回退 modeling-solver）。当前论文已维持充分的定性披露：假设 5（新拆分条目）声明其为关键敏感参数、6.4 节误差来源（3）量化其乐观方向与边界（相对排序不受影响）、7.2 节局限性第一条、改进方向可承接。评审初审亦已按 R-1 减轻情节由 high 降级 medium，维持现状符合该降级逻辑。若复审仍要求数值对照，建议编排器裁决是否二次回退建模。

### M-术语表缺算法术语节 —— 论文侧 fixed / 术语表.json 侧 rejected
- 论文侧（fixed，表达层）：符号说明节原"算法缩写一句话"升级为独立算法术语三线表（表 tab:algo，9 条：MIP/分支定界/McCormick/Stackelberg/纳什均衡鞍点/Dijkstra/Lanchester 平方律/贪心构造/蒙特卡洛），B 题核查 #6 五类术语在论文侧补齐。修复位置：四、符号说明节末。
- 术语表.json 侧（rejected）：该文件生产者为 modeling-solver，R1 权限外；论文符号说明节已与术语表.json 既有五节（索引/决策变量/参数/目标/派生量）保持一致，算法术语以论文表格补足。

### L-符号 z/α 双重使用 —— fixed
- 处置：护航 0-1 变量 z_r 重命名为 e_r（指挥节点 z_c 保留）；Lanchester 火力系数 α_u 重命名为 λ_u（空中上限 α 保留，因 fig14 图内坐标轴标注为 α，改 α 会引入图文新冲突）。符号表补注代码映射（e_r 对应代码 z[r]、λ_u 对应 FIREPOWER），保证代码-论文符号一致性可追溯。
- 修复位置：符号表两行、式 cescort/closs、McCormick 段、MC 验证段、Lanchester 离散格式段，全文同步（grep 复核 z_r/α_u 零残留）。

### L-假设4内容过载 —— fixed
- 处置：原假设 4 拆分为两条——假设 4 战斗损耗规律（Lanchester 平方律+火力系数+防御乘性修正+噪声）、假设 5 守军强度标定（k_def 单列，声明其为 Q3 胜率关键敏感参数并指向误差分析节）。假设总数 6→7，正文"假设 6"交叉引用同步改为"假设 7"。
- 修复位置：三、模型假设节；5.1.2 节交叉引用。

### L-图口径不统一 —— fixed
- 处置：Tornado 图解析段补口径声明（扫描以不含人力口径计算，人力成本占比约两成且不改变敏感度排序，主结论一律含人力 TC_total，两口径可据表 9 换算）；护航临界点解析段补口径说明（人力成本与是否护航无关，两方案同加基线人力成本 49800 元/日后方案差不变，护航恒优结论不受口径影响）。fig5/fig6 caption 原口径声明保留。
- 修复位置：6.2 节两段解析。

### L-75432.2/75432.3 舍入伪影 —— fixed
- 处置：统一为"与 TC_excl_labor 严格自洽"的舍入值——苏军 75432.2（3096.5+9485.0+75432.2=88013.7）、盟军 97816.6（4664.4+15092.0+97816.6=117573.0），表 9 与正文、MC 验证段全部一致；MC 验证段加注"解析值与表 9 的 C_loss 为同一量的统一舍入表述"。两值均在 solution.json 有 source（苏=monte_carlo.analytic_C_loss，盟=cost_decomposition.C_loss）。
- 修复位置：表 9 苏军行、5.2.4 节反直觉发现段、MC 验证段。

### L-solver_backend.py 路径在 project/ 外 —— rejected
- 理由：附录代码采用 \VerbatimInput 直接引用实际源文件是"与实际代码逐行一致"的硬约束实现方式（等效 lstinputlisting，机查 PASS 11 个文件）；solver_backend.py 位于 .trae/code_templates/ 系求解后端模板的真实存放位置，路径组织不影响可运行性（各求解脚本以 sys.path.insert 显式加载该目录，代码内可见）。若拷贝副本入 project/ 反而产生两份代码的一致性维护风险。支撑材料打包时按代码内 sys.path 说明附带该目录即可复现，此点已在附录执行顺序说明中覆盖。

### L-MC 次数建议 —— fixed（表达层）
- 处置：维持 2000 次（偏差 0.72%/1.54% 已达标、SEM 收敛已披露），在 MC 验证段补一句"损失为低频高额复合分布，重尾分布下将仿真次数增至 10^4 以进一步压缩标准误，列为后续工作"。重跑 10^4 次属求解层操作，超出 R1 权限，以诚实披露处理。
- 修复位置：5.2.4 节模型验证（蒙特卡洛）段。

## 全节数值重核发现的连带漂移（H-1/H-2 重跑引发，一并修复）

| 位置 | 旧值 | 新值 | source |
|------|------|------|--------|
| 5.2.4 节 Q2 求解时间 | 0.054 s / 0.059 s | 0.391 s / 0.07 s | solution.json q2_*.optimality.solve_time_s |
| 7.1 节优势"求解时间在 0.3 s 以内" | 0.3 s | 0.4 s | 同上（0.391>0.3，表述修正） |

## 新旧数值对照表（工单核心数值）

| 项 | 旧值（已废止） | 新值 | source 字段 |
|----|--------------|------|------------|
| 苏军 TC_worst | 143734.7 | 165334.7 | q2_soviet.stackelberg_worst_case.TC_worst |
| 盟军 TC_worst | 188914.0 | 217114.0 | q2_allied.stackelberg_worst_case.TC_worst |
| 苏军对抗增幅 | +31.13% | +50.83% | delta_pct |
| 盟军对抗增幅 | +29.59% | +48.94% | delta_pct |
| 苏军绝对增量 | 34121.0 | 55721.0 | extra_loss |
| 盟军绝对增量 | 43141.0 | 71341.0 | extra_loss |
| 不含人力参照增幅 | （未披露） | +63.31%/+60.68%（footnote） | delta_pct_excl_labor_reference |
| 生存概率（畅通） | 0.7548（装备加权） | 0.7956（人员加权） | survival_comm_ok |
| 生存概率（中断） | 0.6276 | 0.6730 | survival_comm_lost |
| 生存差 | 0.1272 | 0.1226 | survival_difference |
| CI95 畅通 | [0.5841,0.9245] | [0.5962,1.0000] | monte_carlo.detail.comm_ok |
| CI95 中断 | [0.4682,0.7930] | [0.4809,0.8640] | monte_carlo.detail.comm_lost |
| SEM/mean | 0.26%/0.29% | 0.29%/0.32% | sem_mean_ratio |
| std/mean | 11.71%/13.15% | 12.78%/14.47% | std_mean_ratio |
| 目标分配 | 80/40/80 单位（断言容量紧） | 40.8/11.3/47.8 万人（占用率 50%，松） | target_allocation_personnel_万人 |
| 殿后 | 1584 单位 | 10 万人 | rearguard_size_万人 |
| 路线 | 10 条、均长 8.479 km | 7 条、均长 13.405 km | n_routes / avg_route_km |
| 风险敏感畅通 | 0.811→0.7035 | 0.8466→0.7506 | sensitivity.data |
| 风险敏感中断 | 0.6893→0.5736 | 0.7314→0.6248 | sensitivity.data |
| C_loss 苏军 | 75432.3（表）/75432.2（解析） | 统一 75432.2 | monte_carlo.analytic_C_loss |
| C_loss 盟军 | 97816.6（表）/97816.4（解析） | 统一 97816.6 | cost_decomposition.C_loss |
| Q2 求解时间 | 0.054/0.059 s | 0.391/0.07 s | optimality.solve_time_s |

## 修复时全局扫描记录（修复回路一致性协议）

修复后对旧值全集（31.13/29.59/143734/188914/34121/43141/0.7548/0.6276/0.1272/1584/8.479/0.811/0.7035/0.6893/0.5736/11.71/13.15/75432.3/97816.4/0.054/0.059）逐方扫描：
- paper.tex：零残留（grep 0 命中）；
- abstract_candidates.md：旧值仅存于"R1 修复记录（已废止）"说明行，合法；
- handoff_notes_2.md：图表清单 fig13/fig8 行已同步新值，页数结构已更新；
- 术语表.json / stage5_review.json：无旧值；
- solution.json / modeling_plan.json：旧值仅存于修复审计轨迹（before/after 对照与"已废止"note），合法。

## 编译与机查

- 编译：xelatex 3 次（MiKTeX 沙箱环境变量固化），0 error，Overfull 0，无 undefined references。
- 页数结构：PDF 89 页 = 摘要 1 页（p1，≤1 达标）+ 正文 28 页（p2-p29，≤28 达标）+ 参考文献 1 页（p30）+ 附录 59 页（p31-p89，11 个源程序 VerbatimInput 完整直引，机查 PASS）。R1 新增内容后正文一度 29 页，按惯例 二.15 以缩小图尺寸（单图 0.55→0.46、流程图 0.75→0.62、大图 0.88→0.80，未删任何验证内容）压回 28 页。
- check_latex_compliance.py（--contest-year=2026）：0 ERROR / 3 WARN / 13 PASS。3 WARN 裁定：①内部高频短语 42 个——均为实义领域术语（指挥节点/部署节点/蒙特卡洛等），合法；②超长段落 6 处——假设 enumerate 列表机查误判 + 连贯论证段（论证完整，记录理由保留）；③PDF 89 页——已人工核对正文 28 页达标。
- check_tex_numbers.py --report：25 WARN（WARN 级不阻塞），逐条裁定均合法：排版参数（2.54/3.18）、字体码位注释（2208/2605/2713）、题目参数（14000）、假设参数（1000/0.0001/0.01/0.012/0.526/19.55/0.09）、派生阈值（0.045/0.0454/0.1638）、百分比表述（46.7/54.61/12.78/14.47/2.74/0.29/0.32）、变量计数（4360）、粒度验证（1e-05）。
- check_pipeline_manifest.py --stage writing --mode competition：0 ERROR / 0 WARN（20 项 checked）。

## 移交复审说明

H-1 修复链路为 modeling-solver 重算真源（solution.json/modeling_plan.json/fig13）+ paper-writer 论文同步，五方中代码与两份 JSON 已由 modeling-solver 修复并附审计轨迹；H-2 同链路（fig8 已重绘）。复审重算修复节数值时请以 solution.json 现行字段为准。
