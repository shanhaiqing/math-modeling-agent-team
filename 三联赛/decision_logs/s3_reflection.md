# S3 反思日志：求解与验证反思（聚焦模式）

题目：红色警戒 B 题 ｜ 日期：2026-08-13 ｜ 执行者：@modeling-solver

---

## 层 1：完整性扫描（12 项）

| # | 检查项 | 判定 | 依据 |
|---|--------|:---:|------|
| 1 | 算法对比表 ≥2 候选且为真实分析 | ✓ | method_card_matching.md 命中卡片 02/06/04/10 各含候选提取与风险点；modeling_plan.alternative_algorithm_discussion 含 DP/MIP时序/贪心三方复杂度对比（Q3）；Q2 基线 vs Stackelberg 双模型对比（multi_model_candidates[0]） |
| 2 | 方法卡片匹配矩阵每卡一行且命中卡片有完整理由 | ✓ | 12 卡逐一点名（01-12 无跳卡），命中 4 卡（02/06/04/10）各含适用条件核对/候选提取/风险点三段 |
| 3 | 代码模板 CORE ALGORITHM 区块未修改 | ✓ | solver_backend.py 以 import 方式调用，solve_mip/validate 原样使用未修改；visualization_style.py 的 save_figure/plot_tornado 原样调用；自建部分（common_data/问题1-3/验证分析/图表生成）为题目专属建模代码，无适用模板（标注：自建理由=题目结构专属，模板库无覆盖型部署 MIP 模板） |
| 4 | 代码含 assert/check_feasibility | ✓ | common_data.py 含 assert（目标节点在主分量）；solver_backend.validate() 在每个求解后调用并写入结果 JSON；问题1 每候选记录 validate_problems 字段 |
| 5 | 图表自检通过 | ✓ | 10 张图全部生成（PDF+PNG 双格式 300dpi）：fig1 部署地图/fig2 构成堆叠柱/fig3 补给网络/fig4 成本分层柱/fig5 Tornado/fig6 临界点/fig7 进攻方案/fig8 生存对比（误差棒）/fig9 算法流程图/fig10 风险敏感性折线；含 ≥1 流程图（fig9）；每子问题 ≥2 图（Q1:fig1-2，Q2:fig3-6，Q3:fig7-8,10）；fig8 用误差棒表达 MC 95%CI |
| 6 | 最优性验证完成 | ✓ | Q1/Q2 全部 status=optimal、MIPGap=0.0（求解器原生元数据，非 LLM 自报）：Q1 苏军 t=0.2s/盟军 0.1s，Q2 双方 t≈0.05s；Q3 贪心无最优保证→以 Lanchester MC 评估+夺控胜率报告（已显式声明） |
| 7 | 模型验证完成 | ✓ | MC 模型验证（Q2）：解析期望损失 vs 伯努利拦截仿真 2000 次，苏军偏差 0.72%/盟军 1.54%（<5%）；Q3 生存概率 MC 各 2000 次；convergence 字段按公式判定（std/mean=46.7%>5% → not converged，已附 sem_note 说明内在离散与均值收敛的区分，未硬编码） |
| 8 | 灵敏度扰动范围与论文将写范围一致 | ✓ | Q2 三参数均含 ±5%(0.95/1.05)/±10%(0.9/1.1)/±20%(0.8/1.2) 点（破交另含 0.5/0.75/1.25/1.5 扩展）；Q1 权重 ±20%；Q3 风险 ±20%；validation_result.json 为唯一数据源，论文引用范围与之一致 |
| 9 | 策略转换临界点全部有 source | ✓ | 护航临界点 critical_risk_scale=0.2，source="验证分析.py q2_escort_critical 扫描"（8 点扫描数据在 validation_result.json.q2_escort_critical.scan）；Q1 指挥节点权重扰动 0 翻转（无临界点，稳健性结论有 perturbation 数据支撑） |
| 10 | 活跃约束已写入 solution.json | ✓ | Q1 苏军 6 条兵力守恒+咽喉覆盖 active（slack=0）、盟军同构；Q2 需求满足约束 active；每条附 slack 数值（求解器原生 c.slack）+派生量（打包时补边际说明） |
| 11 | 多算例 ≥2 场景 | ✓ | 3 场景：基准 / 破交强化 risk×1.5（TC 苏+12.2%/盟+18.9%）/ 需求-10% 预备队情形（TC 苏-10%/盟-10%），数据在 multi_scenario 字段 |
| 12 | 代码-论文一致性预检通过 | ✓ | 代码变量名与术语表映射块在 common_data.py 头部；参数硬编码与 source_parameters 一致（FORCES 12 项/RANGE 火炮 16.8/13.0/TARGET_NODES [352,144,149]/N_AA=10）；打包前机查 check_solution_json.py [一.11] 将复核 |

## 层 2：对抗性深挖

### 必查项 1 三方数值与字段一致性（≥5 个核心参数/结果抽查）

| 数值 | 代码硬编码/计算值 | modeling_plan.json | solution.json（打包值） | 判定 |
|------|------------------|--------------------|------------------------|:---:|
| 苏军 V3 数量 | FORCES["苏军"]["火炮"]=7000 | source_parameters "苏军V3远程火箭车":"7000辆" | q1 部署合计=7000（守恒约束验证） | ✓ |
| 防空据点数 | N_AA=10 | "每方可设置10个防空据点" | aa_nodes 长度=10（双方） | ✓ |
| V3 射程 | ARTILLERY_RANGE["苏军"]=16.8 | "最大射程16.8km" | 覆盖系数预计算用 16.8 | ✓ |
| 转移目标节点 | TARGET_NODES=[352,144,149] | "[352, 144, 149]" | q3 分配键={352,144,149} | ✓ |
| 生存概率差 | 0.7548-0.6276=0.1272 | comparison_plan"均值差" | survival_difference=0.1272 | ✓ |
| MC 偏差 | 苏 0.72%/盟 1.54% | 无（验证层） | mc_validate_q2.deviation_pct | ✓ |

**结构化嵌套字段双查（全字段值+字段类型）**：
- monte_carlo（Q3 comm_ok）：mean_survival=0.7548(float) / std=0.1081(float) / ci95_low=0.5(float) / ci95_high=0.9375(float) / std_mean_ratio=0.1171(float) / convergence="not converged (std/mean=11.71% > 5% threshold)"(str，与 ratio 一致) / n_sim=2000(int) ——类型与值自洽 ✓
- sensitivity（Q2 需求率缩放）：scale=0.8 时 delta_pct=-20.0——与 TC 线性于需求的结构一致（需求×0.8→成本×0.8）✓
- critical_points：critical_risk_scale=0.2，scan 数据中 scale=0.2 行 TC_free<TC_no_escort 成立 ✓

**字段值间逻辑一致性（惯例一.17）**：
- objective_value（Q1 苏 0.7688）vs decision_variables（部署矩阵）vs active_constraints（force_* 全 active slack=0）：部署合计=兵力总量，与守恒约束 active 互相印证 ✓
- best 指挥节点 136 vs command_scores（136 评分 0.7722 为 Top6 最高）vs candidate_eval（136 的 Φ 最优）——三字段指向同一节点 ✓
- Q2 TC_total=109614 vs C_trans+C_escort+C_loss+C_labor=3096+9485+75432+21600=109613（四舍五入差 1）✓

### 必查项 2 调试纪律回溯
- 未发生删约束/缩规模/换更简单算法/创建简化版代码。
- 发生的两次修复均为原文件 bug 修复：①问题1 约束名冲突（throat_229 重复）→ 改为按边索引命名（原文件修复）；②C4 空中上限与 C2 守恒冲突 → 空中改为 ≤ 不等式（原文件修复，建模语义修正而非简化）。
- 论文将描述的算法步骤与主代码实现核对：指挥节点 Top6 候选枚举（问题1_求解.py command_candidates k=6 ✓）、每 OD 3 候选路径（问题2_求解.py K=3 ✓）、MC 2000 次（问题3_求解.py N_MC=2000 ✓）、随机种子 2026（RNG_SEED=2026 ✓）。

### 必查项 3 启发式随机性（条件触发：Q3 贪心+MC）
- Q3 Lanchester 评估用固定种子 2026（可复现）；生存概率 MC 用固定种子。
- 贪心夺控序列为确定性构造（非随机启发式），无需 ≥5 次独立运行统计；其质量以夺控胜率（每步 win_rate）与 Lanchester 仿真评估报告。若后续引入随机扰动搜索，须补 ≥5 次运行统计——当前不适用，判定 ✓（条件触发项已核查）。

### 必查项 4 灵敏度覆盖范围（条件触发：题目含多个含优化子问题）
sensitivity_coverage：
- Q1（含优化）：权重 w ±20%（6 扰动点×2 阵营，0 翻转）+防空半径 ±33% ✓
- Q2（含优化）：破交概率/需求率/车载容量三参数，各含 ±5%/10%/20% ✓（Tornado 图 fig5）
- Q3（含优化：进攻序列贪心+转移分配）：拦截风险 ±20%（生存概率双情景）✓（fig10）
三个含优化子问题全覆盖，每子问题 ≥1 核心参数 ±5%/10%/20%。

## 层 3：红队自查（努力举证制）

**搜查目标**：数值错误致结论不可信、验证缺失、代码与方案脱节。

| 搜查对象 | 检查结论与证据 |
|---------|---------------|
| R1 Q2 目标值与重算 TC 差异 | solver objective=81690 vs 重算 TC_excl_labor=88013（差 7.3%）。根因：护航成本在 MIP 目标中用固定份额（需求/3）线性化，重算用实际流量——属线性化近似偏差而非错误。处置：solution.json 以重算值为准（保守、可行解的真实成本），objective_value 字段附 _note 说明两者关系。判定：已披露，非 high severity |
| R2 MC 收敛字段语义 | Q2 MC 验证 std/mean=46.7%（低频高额损失，复合分布）→ convergence="not converged"。风险：下游误读为"仿真失败"。处置：已加 mean_converged=true（偏差 0.72%<5%）与 note 字段区分"样本内在离散"vs"均值估计收敛"。机查 check_solution_json.py 对 convergence 与 std_mean_ratio 的一致性将复核（公式判定，无矛盾） |
| R3 部署集中度异常 | Q1 部署仅 10-11 个节点（436 中）——火炮 7000 集中于 8 节点（每节点 1050=15% 上限）。核查：这是 NODE_CAP_RATIO=15% 上限约束的直接结果（7000×0.15=1050），数学正确；军事上集中部署有被覆盖风险，但 S_c 目标含防御强度加权且防空 Stage-B 覆盖了这些节点。判定：结构合理，论文须披露集中度（P2 上限的效应） |
| R4 消耗模式车辆数=10 的量级 | 苏军消耗模式仅 10 车/61 人——因战场小（43×26km）、日需求仅 51 吨、周转快（avg_trip≈2.5h→9.4 次/日）。量级核查：51 吨/日 ÷(10 吨×9.4 周转)≈0.54 车/需求节点聚合——合理（小战场高周转）。判定 ✓（量级合理，S3 红队 A-2 条款已执行） |
| R5 生存概率 0.75 的量级 | 畅通 0.7548/中断 0.6276——每路径平均 3-5 跳、每跳拦截概率 0.05-0.15、拦截损失 40%，(1-0.1×0.4)^4≈0.85 每路径，加协同/殿后修正后 0.75 合理；中断情景风险×1.3 且无协同加成 → 0.63。差 0.127 与"通信价值"语义一致。判定 ✓ |
| R6 主攻方向 55→372 的合理性 | 边 55→372：敌防御 0.58（8 条边中中等偏弱）、长度 0.567km（短通道）、评分 0.5133 为 8 条最高。对照最弱防御边 74→366（防御更低但走廊价值低）。贪心评分权衡合理。判定 ✓ |
| R7 活跃约束派生量 | Q1 force_* 约束 slack=0（active）——派生量=部署合计与兵力总量的差（=0，守恒满足）；throat_* slack=0——派生量=覆盖该咽喉的火力单位数（≥1）。打包时写入每条 active 约束的 slack 数值（求解器原生）。判定 ✓ |
| R8 代码-方案脱节搜查 | modeling_plan.Q2"护航 z 为 0-1→MIP" vs 代码 z_r Binary ✓；"McCormick 线性化"vs 代码 mc1/mc2/mc3 约束 ✓；Q1"单目标覆盖上限 3"vs 代码 COVER_CAP=3 与 y_m≤Σcov·x ✓；Q3"殿后 10%"vs 代码 rearguard_fraction=0.10 ✓。无脱节 |
| R9 反直觉结论交叉验证（A-1） | 潜在反直觉点：盟军光棱火炮 14000 门（数量 2 倍于苏军）但 Q2 盟军 TC（145773）>苏军（109614）。交叉验证：盟军部署节点更分散（需求节点多）+盟军火炮射程短（13km）需更靠前部署→路径风险更高。数据支撑：盟军 C_loss=97817>苏军 75432。结论有机制解释+数据支撑，非错误。判定 ✓（已执行交叉验证） |
| R10 结果量级合理性（A-2/M-3） | 全部目标值量级核查：Φ∈[0,1]（0.77）✓；TC 万元/日级（小战场合理）✓；生存概率 ∈[0,1] ✓；车辆/工人数十级（小战场）✓；夺控胜率 0.6-0.9（优势进攻方合理）✓。无 >10 倍异常 |

**红队结论**：R1（目标值-重算差异）已披露处置；其余 9 对象核查通过。0 个 high severity 残留。

---

## S3 结论
层 1 十二项全部 ✓；层 2 四项必查完成（三方数值 6 组+嵌套字段双查+逻辑一致性 3 组；调试纪律 2 次原文件修复回溯；启发式随机性核查；灵敏度三问全覆盖）；层 3 红队 10 对象搜查、0 high severity。具备打包条件。

---

## HG1 退回补执行（2026-08-13，补执行不重建模型）

**退回背景**：HG1 用户裁决六项假设争议点（A-01/A-02/A-03/A-04/A-07/Q2口径）须以"分类介入"方案显式参数化。本节记录补执行的搜查范围、执行证据与结论。

### 执行方式与纪律核查
- 新建 project/HG1_补执行.py：复用 问题1_求解.solve_deployment/place_aa 与 问题2_求解.solve_supply，仅扰动参数重求解，未重建模型结构、未删约束、未缩规模（调试纪律 ✓）。
- 基线复现自检（assert 强制）：苏军 cmd=136/Φ=0.76879、盟军 cmd=384/Φ=0.77324、Q2 TC_excl_labor 苏 88013.7/盟 117573.0——与 q1_result/q2_result 基线完全一致后方可进入 sweep。
- 最优性元数据全部取求解器原生输出：全部 42 个 sweep 求解点 status=optimal、MIPGap=0.0（solver_meta 字段逐点登记 max_solve_time_s≤0.4s）。
- 执行中两次 bug 均原文件修复：①stdout GBK 编码崩溃→reconfigure utf-8；②Q2 传播部署聚合 setdefault 单行写法 KeyError→拆两步；③A-07 结论文本"0.01"与结构化字段 phi_delta=0.0001 不匹配（P-2 WARN）→改为动态引用 max_phi_delta。无简化绕过。

### 搜查范围与证据（红队自查，努力举证制）
| 搜查对象 | 检查结论与证据 |
|---------|---------------|
| H1 A-02 sweep 是否真重解模型 | 每扫点重建覆盖系数 cov（RANGE 补丁生效）→逐候选重解 MIP。结果：d∈[1.0,3.0]km 5 点双方 Φ 恒定（苏 0.7688/盟 0.7732）、指挥节点 0 翻转、部署 Jaccard=1.0。机理核查：坦克直射 1-3km 仅影响对 8 条跨阵营边敌端点的直接覆盖，而咽喉覆盖约束与火炮射程（16.8/13.0km）主导部署结构，故解不变——非脚本失效，是结构稳健的真实证据。稳定性区间：苏军/盟军均为 [1.0,3.0]km（全扫描区间），翻转计数=0 |
| H2 A-03 sweep 是否真重布置防空 | 每扫点以 R_AA 补丁重解 Stage B 最大覆盖 MIP。结果：r∈[2.0,4.0]km 5 点防空节点集 Jaccard=1.0、S_bonus 恒定（苏 803.5/盟 1559.4）。机理核查：部署仅 10 节点且两两间距<2km（NODE_CAP 集中部署），r≥2km 时 10 据点已全覆盖部署兵力，半径不再起区分作用——与上一轮 aa_radius_perturbation（±33% phi_delta=0）互相印证。稳定性区间：双方 [2.0,4.0]km |
| H3 A-04 sweep 是否产生真实响应 | α∈[5%,20%] 4 点：空中部署 25/50/75/100（苏）、15/30/45/60（盟）随上限单调变化，Φ 微升（苏 0.7683→0.7698），指挥节点 0 翻转；Q2 传播 TC 最大变化 0.419%（苏 α=20%）——定性结论（空中少量集中、非主力）稳定。稳定性区间：双方 [5%,20%] 全域 |
| H4 A-07 验证算例是否改变结构 | 0.5 万人粒度（动员兵×2）：指挥节点不翻转（136/384）、装备部署 Jaccard=1.0、Φ 最大变化 0.0001、动员兵分配 L1 差 6 万人（苏，125 万中占 4.8%，为粒度细分的正常再分配）。结论：万人粒度属粒度选择而非精度损失，结构稳健 ✓ |
| H5 A-01 对照数值一致性 | 结构化登记 TC_baseline vs TC_worst：苏 109613.7→143734.7（+31.13%）、盟 145773.0→188914.0（+29.59%）——与 handoff_notes 所述"+31%/+30%"一致，数据源 q2_result.stackelberg_worst_case（上一轮已求解，本次仅结构化登记未重算） |
| H6 合并是否破坏既有契约字段 | merge-only 就地注入 sensitivity 新键（direct_range_sweep_A02/aa_radius_sweep_A03/air_cap_sweep_A04/baseline_vs_stackelberg_A01/air_cap_alpha_sweep_A04），既有 8 契约字段未动；机查复核：check_solution_json.py 0 ERROR/2 WARN/41 PASS（2 WARN 为 Q1 monte_carlo=null 既有提示，已附"确定性MIP不适用"说明，属已知虚惊）；check_pipeline_manifest.py --stage modeling --mode competition：0 ERROR/0 WARN（术语表双份问题未复发，根目录无 术语表.json，唯一路径 result_bundle/术语表.json） |
| H7 新图合规性 | fig11（A-02 sweep 折线+稳定区带）/fig12（A-03 sweep 双轴）/fig13（A-01 基线 vs Stackelberg 分组柱+Δ%标注）/fig14（A-04 sweep 双轴）：PDF+PNG 双格式 300dpi、visualization_style.py 风格（SciencePlots+中文字体）、bundle figures PDF 总数 10→14 |

### 补执行结论
六项争议点全部按"分类介入"落地：A-01/A-02/A-03/A-04 显式参数化（parameter_registry 四字段齐全+sweep 数据入 solution.json sensitivity），A-07 粒度验证算例与 Q2 口径注记入 modeling_plan.verification。全部 sweep 显示部署结构对四项参数在扫描域内稳健（0 翻转/0 布局变化）。两次机查 ERROR 清零。红队 7 对象搜查、0 high severity。

---

## BLOCKED 回退修复（2026-08-14，初审 H-1/H-2，编排器裁决口径）

**回退背景**：@independent-reviewer 初审发现两条 high severity（H-1 Stackelberg 口径混用、H-2 Q3 转移混合量纲），编排器裁决回退 @modeling-solver 重建口径。本节记录修复的搜查范围、重算证据、口径裁决与验证结论。

### 口径裁决记录（编排器 2026-08-14）
- **H-1 主口径=含人力 TC_total**（与 Q2 objective_value 一致）：TC_worst（含人力）= 基线 TC_total + extra_loss；delta_pct 两方重算。
- **H-2 人员口径重建**：转移分配以人员（万人/建制）为决策量纲；装备随建制伴随转移，容量按车辆数/吨位单独核算并报告占用强度；生存概率改为人员加权（人员生存概率）；两情景各 2000 次 MC 重跑（种子 2026）；人员口径下"容量紧"不成立则删除该断言并如实报告占用率。

### H-1 修复与重算证据
- **根因**：问题2_求解.py stackelberg_worst_case 原实现 TC_worst=TC_excl_labor+extra_loss，而论文/摘要以含人力 TC_total 为分母报增幅，分子分母口径混用，任何单一口径下不自洽。
- **修复**：stackelberg_worst_case 改为 TC_worst=base_result["TC_total"]+extra_loss，并新增 caliber/TC_baseline/delta_pct/TC_excl_labor_baseline/delta_pct_excl_labor_reference 字段；main() 中将 Stackelberg 调用移至 C_labor/TC_total 计算之后（原顺序 TC_total 尚未生成）；加 assert 防口径回归。
- **重算结果（代码原生输出）**：苏军 TC_worst=165334.7（109613.7+55721.0），delta=+50.83%；盟军 TC_worst=217114.0（145773.0+71341.0），delta=+48.94%。不含人力参考口径 +63.31%/+60.68% 一并登记（delta_pct_excl_labor_reference）。
- **与 reviewer 参考值核对**：reviewer 独立重算 +50.83%/+48.94%——与本次代码重算**完全一致**（0 偏差）。
- **同步**：solution.json q2_*.stackelberg_worst_case 与 sensitivity.baseline_vs_stackelberg_A01（三字段两方）、modeling_plan.json parameter_registry.A-01（range/range_numeric 动态生成）、fig13 重绘（PDF+PNG）。

### H-2 修复与重算证据
- **根因**：force_vector 将动员兵（万人，100）与装备（辆/门/架，15740）直接相加=15840（混合量纲）；容量合计 200 仅占 1.26%，"容量约束全部紧"断言不成立；survival_mc 生存概率实为装备加权（火炮 14000 占 88.4%）未披露。
- **修复**：新增 personnel_by_node（人员口径）与 equipment_by_node（装备口径）分离聚合；withdrawal_comm_ok 以人员（万人）为决策量纲做防御强度+容量加权比例分配，装备随建制伴随（按人员份额比例随迁，报告口径）；survival_mc 改为人员加权（各部署节点动员兵万人占比 w_n，整体人员生存概率=Σw_n×纵队存活率），两情景各 2000 次重跑（种子 2026）；验证分析.py sensitivity_q3 改为复用 survival_mc（人员口径，禁止另写混合量纲仿真）。
- **重算结果（代码原生输出）**：人员总量 100 万人（守恒 assert 通过）；分配 352:40.8/144:11.3/149:47.8 万人；人员容量占用率 50%（总容量 200 万人 > 总人员 100 万人，容量为松）；人员生存概率 畅通=0.7956/中断=0.6730，差 0.1226（各 2000 次 MC，种子 2026）。装备占用强度：78.55 辆/万人容量、631.7 吨/万人容量（报告口径，题目未给车辆/吨位容量，不设车辆容量约束）。
- **"容量紧"断言处置**：**删除**。人员口径下容量为松（占用率 50%），solution.json capacity_tight_assertion 字段与 active_constraints（三节点 active=false，slack=39.2/28.7/32.2 万人）如实记录；装备占用强度见 equipment_accompanies。
- **同步**：solution.json q3_allied_withdrawal 全字段（objective_value/decision_variables/monte_carlo/active_constraints/sensitivity）、modeling_plan.json Q3 withdrawal 节与 indicator_dimension_check、fig8 重绘（PDF+PNG）、术语表 P_surv 条目。

### 搜查范围与证据（红队自查，努力举证制）
| 搜查对象 | 检查结论与证据 |
|---------|---------------|
| B1 H-1 数值三方一致 | 代码重算（165334.7/217114.0，+50.83%/+48.94%）vs solution.json baseline_vs_stackelberg_A01 vs modeling_plan parameter_registry.A-01——三方数值一致；与 reviewer 独立重算参考值 0 偏差 |
| B2 H-1 口径自洽性 | TC_worst−TC_baseline=extra_loss（苏 55721.0/盟 71341.0）恒成立；delta_pct=extra_loss/TC_baseline×100 分子分母同口径（含人力），不再混用；assert 防回归 |
| B3 H-2 人员守恒 | personnel_by_node 合计=100 万人=FORCES["盟军"]["动员兵"]（assert 通过）；装备口径单独聚合（15740 辆/门/架，含空中 30），不再与人员相加 |
| B4 H-2 生存概率加权口径 | survival_mc weights=各节点动员兵/总动员兵（人员加权），weighting 字段显式登记；修复前装备加权口径已废止并在 note 标注 |
| B5 H-2 容量断言与占用率 | 人员容量占用率 50%（松）；"容量紧"断言删除；装备占用强度如实报告（78.55 辆/万人容量、631.7 吨/万人容量）；active_constraints 三节点 active=false+slack 数值 |
| B6 MC 元数据原生性 | 两情景 n_sim=2000/seed=2026 取代码常量；convergence 按 std/mean 公式动态判定（12.78%/14.47%，not converged）；sem_mean_ratio 一并报告；无硬编码 converged |
| B7 灵敏度口径一致 | 验证分析.py sensitivity_q3 复用 survival_mc（人员口径），scale=1.0 点 0.7977/0.6742 与主运行 0.7956/0.6730 在 MC 噪声内一致（n_sim=1000 vs 2000）；fig10 数据同源 |
| B8 调试纪律回溯 | 未删约束/缩规模/换更简单算法/创建简化版代码；H-1/H-2 均为原文件口径重建修复（问题2_求解.py/问题3_求解.py/验证分析.py/HG1_补执行.py/打包.py/图表生成.py），模型结构未变 |
| B9 唯一路径核查 | modeling_plan.json 唯一路径 result_bundle/（HG1_补执行.py 与 打包.py 已改为就地读写 result_bundle/，禁止根目录副本）；术语表唯一路径 result_bundle/术语表.json；figures 唯一路径 result_bundle/figures/ |
| B10 机查复核 | check_solution_json.py：0 ERROR/2 WARN/41 PASS（2 WARN 为 Q1 monte_carlo=null 既有提示，已附"确定性MIP不适用"说明，属已知虚惊）；check_pipeline_manifest.py --stage modeling --mode competition --report：0 ERROR/0 WARN |

### 修复结论
H-1/H-2 两条 high severity 均按编排器裁决口径重建并重跑：H-1 含人力口径 delta_pct 苏 +50.83%/盟 +48.94%（与 reviewer 参考值 0 偏差）；H-2 人员口径重建，人员生存概率 0.7956/0.6730（差 0.1226），容量占用率 50%（松），"容量紧"断言删除。数值真源（solution.json/modeling_plan.json/fig13/fig8/术语表）已同步。两次机查 ERROR 清零。红队 10 对象搜查、0 high severity 残留。论文与摘要的数值同步由 paper-writer R1 执行（本 agent 不改 paper.tex）。
