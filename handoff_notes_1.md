# handoff_notes_1.md（modeling-solver → paper-writer）

## 方法论洞察
1. **几何核验先行**：603 条边"链路长度/坐标欧氏距离"比值恒为 1.0000，直接确立坐标单位=km，使射程覆盖判定可用欧氏距离，免去路网距离的 O(n²) 预计算——数据自洽性核验是本题建模的地基。
2. **图结构即战术**：BFS 发现苏军 23 节点孤立后方分量与 8 条跨阵营前线边，这两个结构特征分别决定了"就地防御部署"与"咽喉火力聚焦+破交风险集中"，是贯穿三问的叙事主线。
3. **线性化换可解性**：WTA 原生 Π(1-p) 非线性目标以"覆盖次数上限 3 的有效覆盖"线性化，436 节点规模 MIP 在开源求解器 0.2s 内证明最优（MIPGap=0）——数模竞赛中"结构线性化+原生最优性证明"远优于启发式。

## 反直觉发现
1. 盟军火炮数量 2 倍于苏军（14000 vs 7000），但后勤总成本反而更高（145773 vs 109614 元/日）——射程短（13 vs 16.8km）迫使靠前部署、路径风险更高，C_loss 主导。论文可作"数量优势≠后勤优势"的亮点讨论。
2. 护航临界点在 risk 缩放 0.2 处——基线环境深处护航区，护航不是可选项而是必需项。

## 建议论文重点展开方向
- 问题 2 的成本四分层结构（运输/护航/破交损失/人力）与 Stackelberg 最坏情形对比（基线 vs 对抗 TC 差约 +31%/+30%）。
- 问题 3 通信畅通 vs 中断生存概率差 0.1272（0.7548 vs 0.6276，各 2000 次 MC）——"通信的生存价值"量化是情感与学术双高点。
- 蒙特卡洛 convergence 双口径披露（std/mean 内在离散 vs SEM 均值收敛）是方法学严谨性加分项。

## 已知潜在质疑点
**论文讨论项**（仅需论文展开论证）：
- 坦克直射距离（1.5/2.0km）与防空半径（3.0km）为假设 A-02/A-03（题目数据缺口），已有 ±33~50% 敏感性覆盖。
- MC 收敛字段 not converged 的内在离散解释（已附 sem_note）。
- 主攻边评分差仅 0.0227（55→372 vs 251→166），论文须讨论次优边翻转条件。

**建模遗留项**（建模未完全解决，需 paper-writer 重点关注）：
- Q2 的 MIP 内部目标值（81690/117573）与重算 TC（109614/145773）差约 7%（护航成本固定份额线性化近似）——solution.json 以重算值为准并附 mip_objective 字段与 _note，论文引用时须用 TC_total 并说明口径。
- Q3 守军强度标定（k_def=0.5+0.3d）为假设，夺控胜率 0.98-1.0 对标定敏感，论文须声明该局限。

## HG退回反馈（2026-08-13，HG1 用户裁决）

**退回理由**：用户裁定六项假设争议点（A-01/A-02/A-03/A-04/A-07/Q2口径）应以显式未知参数形式介入模型，采用"分类介入"方案；当前"单点基线值+敏感性"的表述不够显式，须升级为参数表+取值范围+稳定性区间/最坏情形的规范形态。

**整改要求**（不重建模型，补执行）：
1. **A-01 破交概率**：显式声明为内生未知参数——静态 risk_e 基线仅为"主模型输入"，Stackelberg 最坏情形（TC +31%/+30%）为其鲁棒性成本量化；在 modeling_plan.json 新增参数化节（parameter_registry：每项含 baseline/range/propagation/role），并在 solution.json 的 sensitivity 中补"基线 vs 对抗"对照数据。
2. **A-02 直射距离**：正式参数化 sweep（d∈[1.0,3.0]km，≥5 个扫点），给出"推荐部署 0 翻转"的稳定性区间，数据写入 solution.json 对应子问题 sensitivity。
3. **A-03 防空半径**：同法 sweep（r∈[2.0,4.0]km，≥5 个扫点），输出稳定性区间。
4. **A-04 空中单位上限**：α∈[5%,20%] sweep（≥4 个扫点），确认定性结论稳定。
5. **A-07 万人粒度**：不做参数化（属建模粒度选择而非未知参数），跑一次更细粒度（如 0.5 万人）验证算例，确认部署结构稳定，结果写入 modeling_plan.json 的 design_critique 或新增 verification 节。
6. **Q2 口径**：不做参数化（属计算保真度问题），维持"以重算真值 TC 为准"现状。
7. 更新 solution.json / modeling_plan.json 后重跑 check_solution_json.py 与 check_pipeline_manifest.py --stage modeling，ERROR 清零；若 sweep 产生新图，按 PDF+PNG 双格式入 result_bundle/figures/ 并更新图表清单。
8. 完成后在 s3_reflection.md 或新增日志中记录本次补执行的搜查范围与结论。

## BLOCKED 回退反馈（2026-08-14，初审 H-1/H-2，回退对象=@modeling-solver）

**触发者**：@independent-reviewer 初审（review_report.json，均附独立重算证据）。**编排器裁决**：回退建模重建，口径选择如下。

**H-1 Stackelberg 口径混用（必修）**：
- 现状：代码 TC_worst=TC_excl_labor+extra_loss，增幅 31.13%/29.59% 以含人力 TC_total 为分母，任何单一口径下不自洽；含人力正确值 +50.83%/+48.94%，不含人力 +63.31%/+60.68%。
- 裁决：**主口径=含人力**（与 Q2 主报告口径 TC_total 一致）。重算 TC_worst（含人力）= 基线 TC_total + extra_loss，更新 solution.json q2_*.sensitivity 的 baseline_vs_stackelberg_A01（TC_baseline/TC_worst/delta_pct 三字段两方）、modeling_plan.json 对应表述、fig13 图数据并重绘（PDF+PNG 双格式）。
- 论文/摘要同步由 paper-writer R1 执行，你只负责 solution.json/modeling_plan/fig13 三方的数值真源修正。

**H-2 Q3 转移混合量纲（必修）**：
- 现状：force_vector 万人+车辆相加=15840；容量合计 200 仅占 1.26%，"容量约束全部紧"断言不成立；生存概率实为装备加权（火炮 88.4%）未披露。
- 裁决：**人员口径重建**——转移分配以人员（万人/建制）为决策量纲，装备随建制伴随转移（容量按车辆数/吨位单独核算并报告占用率）；生存概率改为**人员生存概率**（按人员加权），两情景各 2000 次 MC 重跑（种子沿用 2026）；更新 solution.json q3_allied_withdrawal（objective_value/decision_variables/monte_carlo/active_constraints 全字段）、fig8 重绘、modeling_plan 对应节。
- 若人员口径下"容量紧"仍不成立，删除该断言并如实报告容量占用率。

**执行要求**：
1. 修复 问题2_求解.py / 问题3_求解.py 后重跑，optimality/MC 元数据仍取求解器/仿真原生输出；
2. 更新 solution.json + modeling_plan.json（唯一路径 result_bundle/，禁止根目录副本）+ fig13/fig8 重绘入 result_bundle/figures/；
3. 重跑 check_solution_json.py 与 check_pipeline_manifest.py --stage modeling --mode competition，ERROR 清零；
4. s3_reflection.md 追加"BLOCKED 回退修复"节（搜查范围+重算证据+口径裁决记录）；
5. 完成后返回：H-1 新 delta_pct 两方数值、H-2 新生存概率两情景数值与容量占用率、机查计数、更新文件清单——供 paper-writer R1 五方同步与 reviewer 复审。
