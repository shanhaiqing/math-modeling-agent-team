# 赛制卡 · 数维杯国际 / 秋季英文（`shuwei_en`）

> `contest_profile=shuwei_en` 时，paper-writer / FIGURES / reviewer / 合规机查**必读**本卡。
> 与 `国赛公开惯例.md`、`LaTeX格式规范.md` 冲突时**以本卡为准**。缺省 `cumcm` 不读本卡。
> 口径来源：2025 年第十一届数维杯（秋季赛）论文格式规范 + 官方 `swmcmthesis`。2026 当届通知若改页数/页眉/目录，覆盖下表数字并在本段改日期。

## 语言与模板

| 项 | 要求 |
|----|------|
| 全文语言 | 英文（图内、caption、轴标、图例、callout 均禁止中文） |
| 正文字体 | 可读西文衬线，至少 12 pt（官方：Times New Roman；本模板走 `swmcmthesis` + `newtxtext`） |
| 写作起点 | `.trae/code_templates/paper_shuwei_template.tex` |
| 文档类 | `swmcmthesis`（cls/cfg 在 `.trae/code_templates/shuwei/`，编译前拷到与 `paper.tex` 同级） |
| 编译 | `pdflatex paper.tex` 两次。不要用 `ctexart` / 不要当国赛中文卷编 |
| 身份 | 只填 `\baominghao`（队号）与 `\zubie`（题号）。禁止学校 / 队员 / 导师宏与任何身份信息 |
| 去 AI 味 | `.trae/papers/去AI味写作规范_en.md`（不读中文版；机查 7/12 随 `--contest-profile=shuwei_en`） |
| 摘要守护 | `check_abstract_guard.py audit/verify --contest-profile=shuwei_en`（认 `\abstract`/`\keywords`；不套国一中文字符窗） |
| 文献括注 | `citation_check.py --contest-profile=shuwei_en`（跳过纯西文 `(Author, 2023)`；汉字括注仍提点） |

## 页面结构

1. **第 1 页 Summary Sheet**：`\maketitle`（题号、队号、年份、标题、Summary、Key word）。摘要必须一页；机查锚点 `\label{abstract:end}` 放在 `\abstract{...}` 末尾，不得删。
2. **第 2 页 Content**：必须 `\tableofcontents`。
3. **第 3 页起正文**：页眉 `Team # <队号>` + `Page x of y`（cls 在 `\maketitle` 后切换）。封面与目录页 empty，与 2025 优胜卷 2515181 一致。
4. **附录**：本系统仍要求写在 PDF 内（支撑材料三线表 + `\VerbatimInput` 直引 `project/`）。官方允许附录改放支撑包，但缺可运行源程序仍可取消评奖——不要省略附录。

## 页数（与国赛不同）

| | `cumcm` | `shuwei_en` |
|--|---------|-------------|
| 计数 | 摘要页之后、附录前的正文 | **Summary + Content + 正文**（`appendix:start - 1`） |
| 上限 | 正文 ≤30（建议 ~20） | **≤25**（2025 秋季规范；附录不计） |
| 下限 | 正文 ≥10 | 官方无下限；不要为压页删验证项 |
| 目录 | **禁止** `\tableofcontents` | **必须** |
| `\maketitle` | **禁止** | **必须** |
| 页眉 | 无；页脚居中页码 | 正文页必须有队号 + Page x of y |
| 标题编号 | 一、（一） 1 | `1.` / `1.1`（Title Case） |
| 摘要字数 | 中文 400–800 | **不套**该区间；硬约束是 Summary **一页**且结论定量 |
| 文献体例 | GB/T 7714 | 官方三条（书 / 刊 / 网页），正文方括号按引用序 |
| 附录注释语言 | 可中文 | 随正文英文；仍须与 `project/` 逐行一致 |

机查：`python .trae/code_templates/check_latex_compliance.py paper.tex project/ --contest-profile=shuwei_en --contest-year=<赛题年>`。

## 章节骨架（优化类，不抄 2025B 深度学习卷）

Introduction（Background / Problem Restatement）→ Problem Analysis（研究内容导向小节标题，禁止 `Analysis of Question 1`）→ Model Assumptions → Notation → Model Formulation and Solution（按问：建立 / 求解 / 最优性验证 / 模型验证含蒙特卡洛）→ Sensitivity and Error Analysis → Model Evaluation → References → Appendix。

灵敏度、最优性验证、模型验证**不得删**。图表 ≥6，每图 caption 英文、解析 ≥150 词。

## 出图

`shuwei_en` 下轴标、图例、callout、色条标注全部英文；图内禁止任何 CJK。仍禁止图内再放论文大标题。

- 样式：`visualization_style.setup_style()` 读 `pipeline_state.json`，用 Times 系衬线，**不**把 SimSun 放进回退栈；系统无 CJK 字体不报错。
- 自检：`audit_figure` / `visual_qa.py scan --contest-profile=shuwei_en` 图内或 PDF 抽出 CJK → ERROR。
- TikZ：`pdflatex` 编译配方（不加载 `ctex`）；节点文字英文。
- 细则见 `figure-studio/SKILL.md` 条件句。国赛缺省路径仍走 SimSun + xelatex。

## 提交文件名（2025 口径，当届通知覆盖）

论文 PDF：`{题号}SHUWEICUP{队号}.pdf`，例如 `BSHUWEICUP26XXXXXX.pdf`。Summary 必须是该 PDF 的第一页，不得拆成两个文件。
