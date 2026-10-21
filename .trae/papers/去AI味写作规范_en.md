# 去 AI 味写作规范（英文 · 数学建模竞赛垂直版）

**用途**：`contest_profile=shuwei_en` 时，paper-writer 按本规范写英文正文，阶段 5 自审以本黑名单为准；independent-reviewer 5c 对照本文件。缺省 `cumcm` **不读**本文件，改读《去AI味写作规范.md》。

**来源**（蒸馏，不原样装 skill）：[academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer) v0.3.3 Layer 1–4（MIT）；[Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) 与 [blader/humanizer](https://github.com/blader/humanizer) 词表；Kobak et al., *Science Advances* 2025 风格超额词。结构同构于中文规范；数模特有模式由中文第三节英译并收紧主张↔证据。

**明确不做**：不装并行 Cursor skill；不优化 GPTZero；不注入个性/口语/第一人称单数；不把 NSF/NIH 基金腔写进赛文；不改数字、公式、引用。

**引用入口**：国赛公开惯例 二.16 的 `shuwei_en` 条件句；细则以本文件为准。

---

## 一句话速查

直接陈述、数字扛主张、禁套话连用、`we` 与合法 hedging 保留、术语全文同一词。细则在下列章节。

---

## 一、禁用词汇（空洞套话；实义豁免）

- **连接与填充（尤其句首连用）**：Moreover / Furthermore / Additionally / In addition / In particular / In conclusion / To summarize / It is worth noting that / It should be emphasized that / Notably, / Importantly, / in order to（可改为 to）
- **AI 风格动词/名词**：delve / underscore（抽象强调）/ showcase / highlight（句尾假深度）/ foster / leverage（填料）/ tapestry / testament / landscape（抽象格局）/ realm / seamless / intricate / pivotal / groundbreaking / vibrant
- **空洞拔高**：paves the way / sheds light on / of paramount importance / bridges the gap / has the potential to revolutionize / opens new avenues / in today's world / plays a vital/crucial/key role（无对象）
- **空范围与空实验**：extensive/comprehensive/thorough experiments / a wide range of / numerous / various aspects / multiple factors（不点名）
- **系动词回避**：serves as / acts as / stands as / is a testament to（能写 is / has 就不要换）

**豁免**：黑名单打的是空洞修饰。固定术语与统计实义不受限——如 `significant` 有检验、`critical` 在 critical point / critical path、`landscape` 若是地理题本义、`underscore` 若是 LaTeX `\_`。Kobak 常见风格词 `findings / potential / within / across` **单用不定罪**，与其它套话共现再改。

**密度原则**（Wikipedia）：一两个词可能碰巧；同段堆几个才是信号。机查 7 是精简词表 WARN，人工按共现裁定。

---

## 二、禁用句型

- **否定式排比**：禁止 not only … but also / not just X, but Y / this is not …, but …。直接说事实。
- **三段式注水**：禁止强行 A, B, and C 的空洞三连（accurate, robust, and efficient）。两项或四项优于三项；实义并列（initial value, step size, and tolerance）保留。
- **虚假范围**：禁止 from X to Y 的空跨度（from theory to practice），除非 X、Y 是有刻度的量。
- **公式化开头**：禁止 In recent years, X has attracted increasing attention / With the rapid development of / Despite recent advances。从约束冲突、数据观察或可行域缺口切入。
- **句尾 -ing 假深度**：禁止 …, highlighting/underscoring/emphasizing/showcasing …。深度用数字或引用给。
- **模糊归因**：禁止 experts argue / studies have shown（无 \cite）。必须给出条目。
- **过度限定**：禁止 somewhat / relatively / fairly / to some extent 叠用。一个 may 或 about 足够。
- **贡献清单套话**：禁止 (1) a novel method; (2) extensive experiments; (3) promising results。每条贡献必须点名结果与口径。
- **挑战与展望**（机查 7 出 In conclusion / paves the way 时按此人工裁，不一刀切）：
  - **禁止**：The future looks promising / future work can further optimize the model（无对象）。
  - **保留**：Despite relaxing the budget, the objective fell about 12%, which identifies money as the binding constraint; a two-stage stochastic program could absorb demand shocks.

---

## 三、数学建模特有模式（通用学术 humanizer 未覆盖）

- **四连 First, … Second, … Third, … Finally**：拆成两层或并列事实。两层可用。
- **公式化方法句**：This paper proposes a Y method based on X → 从本题决策变量、约束或数据缺口写起。
- **万能评价**：The proposed method has obvious advantages → 在基准参数下，目标值较启发式基线下降 8.3%（给数、给对比口径）。
- **无数据对比词**：significantly better / substantially improves / effectively enhances 无数值 → 必须配数与基准。`significant` 有 p 值或置信区间则保留。
- **prove / demonstrate**：MIPGap $=0$ 或枚举完备可写 solved to proven optimality / the enumeration is complete。蒙特卡洛、启发式、灵敏度只能 show / the sample indicates / under these draws。禁止 We prove the heuristic is optimal。
- **主张↔证据**（academic-humanizer Layer 4）：每条经验主张必须能指到数字、图、表或 \cite；动词不得强于证据。缺证据则补指针或降级动词，禁止补造数据。
- **验证项不得空写**：最优性、模型验证（蒙特卡洛）、灵敏度必须具体（次数、MIPGap、扰动区间），禁止 extensive experiments 一带而过。

---

## 四、真实感与学术文体（保留学术，不写成博客）

- **中性精确就是人味**。禁止为去 AI 味而改口语、幽默、I think、感叹。
- **we 与被动都合法**。We formulate … 与 Samples were normalized … 都可；不要为了「像人」删 we。
- **合法 hedging 必须留**：suggests / is consistent with / may indicate。不要改成 prove。
- **解释性判断给数据**：The budget constraint is binding: relaxing it cuts the objective by about 12% 优于 This result is surprising。
- **句长变化**：同段连续 3 句词数差都 <8 → 拆、并或插一句短句。AI 常把 3–4 个从句堆进一句（约 >30 词）→ 拆开。
- **术语身份**：同一概念全文同一英文词（decision variable 不要下一段改成 decision parameter）。这是「禁止刻意换词」，与中文同义词循环同一条。
- **永不改数字、公式、引用键**。润色只动虚词与套话。

体例：Summary 先行、结果向前、短句直接（近 MCM / ICLR，不近 Nature 散文）。摘要仍走《摘要写作规范》的量化门，不靠本词表硬改 Summary。

---

## 五、标点（与中文规范互斥）

- **引号**：英文半角 `"..."` 或 LaTeX ``` `` '' ```。禁止中文全角 “” 与「」。
- **省略号**：英文三点 `...` 或 `\ldots` 允许。禁止中文六点 ……。
- **数字区间**：LaTeX 用 `--`（2--6\%）。这不是 AI 破折号。
- **破折号**：不学 academic-humanizer 的「全部删除」。禁止同句堆两个 em-dash；揭示性 “the key is—” 仍避免。总量不作中文那条 ≤25 的硬机查。
- **加粗/emoji/聊天腔**：正文禁止 emoji；禁止 I hope this helps / as an AI language model。

---

## 六、内部高频短语与超长段落（机查化）

- **内部高频短语**：同一 **2–4 词**英文短语（黑名单之外）正文出现 ≥5 次 → 将部分实例换成具体指代，**术语身份豁免**（Monte Carlo、decision variable、objective function 等保留）。
- **超长段落**：正文单段超过 **180 词**（去 LaTeX 命令后）→ 拆分或记录理由。不套中文 300 字、不做四字 n-gram。
- 两项由 `check_latex_compliance.py` 检查 12 在 `--contest-profile=shuwei_en` 下执行（WARN）。

---

## 七、阶段 5 快速自查清单

- [ ] 连续三句结构/长度几乎一样？→ 打断一句
- [ ] 句首 Moreover / Furthermore / Additionally 连用？→ 删连接词，让逻辑自己接
- [ ] not only … but also / 空洞三连？→ 直接陈述
- [ ] In recent years / This paper proposes a … based on …？→ 换切入
- [ ] The results show that the proposed method … 无数字？→ 换口径+数值
- [ ] prove/demonstrate 用在启发式或仿真上？→ 降为 show
- [ ] 局限是否具体？→ 点名未建模的机制或失效区间
- [ ] 按第一节词表 Grep（大小写不敏感）？→ 空洞用法替换，实义保留
- [ ] 数字/引用是否被润色改掉？→ 立刻改回

---

## 八、改写示例（模型评价段）

**改写前（AI 味）**：

> In conclusion, the proposed method, which is based on an improved genetic algorithm, is of paramount importance. The results show that it not only improves efficiency but also has significant practical value. Moreover, it paves the way for future research. This novel framework underscores the theoretical and practical significance of our work.

**改写后**：

> Combining the genetic algorithm with simulated-annealing local search cut the median solve time in 250 random starts from 4.2 min to 1.8 min, and the mean gap to the best known solution from 3.1\% to 1.4\%. The model does not reschedule under demand shocks; when daily volume varies by more than 30\%, a fixed location plan needs a separate check. A two-stage stochastic program could take that uncertainty.

**改动要点**：删 In conclusion / paramount / not only…but also / Moreover / paves the way / novel / underscores；空句换数字；局限与后续都点名对象。未改任何原有数值。

---

## 九、机查同步声明

- **已机查（shuwei_en）**：检查 7 英文精简词/句（Furthermore, Moreover, It is worth noting, In conclusion, delve*, underscore*, not only…but also, paves the way, In recent years, to the best of our knowledge）；检查 12 为 2–4 词短语 ≥5 次与超长段落 >180 词。
- **暂人工**：第一节扩展词表、第三节数模特有模式、主张↔证据、标点。
- 缺省 `cumcm` 检查 7/12 **行为不变**（中文六词 + 四句型 + 四字 n-gram + 300 字）。
- 脚本与本文档语义冲突时以本文档为准改脚本。
