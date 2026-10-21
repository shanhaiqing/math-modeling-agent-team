# Phase 2C：技能蒸馏记录

## 做了什么

把 7 个“薄 skill”改成自包含结构：

```text
.dsh/skills/<role>/
  SKILL.md              # 角色流程、阶段、工具、边界（≤4KB）
  references/           # 领域知识、规范、检查单、方法卡
  scripts/              # 仅 figure-studio：visual_qa / visualization_style
```

### 各 skill 的 references

| Skill | references |
|---|---|
| `solver-opt` | `opt-playbook.md`、`optimization-conventions.md`、`optimization-decision-tree.md`、`method-cards/`（12 张）、`paper-index.md` |
| `solver-stats` | `stats-playbook.md`、`data-conventions.md`、`data-decision-tree.md`、`method-cards/`（14 张）、`paper-index.md` |
| `method-critic` | `method-studio.md`、`gate-opt.md`、`gate-stats.md` |
| `figure-studio` | `figure-playbook.md`、`chart-library.md`、`figure-design.md`、`tikz-heroes.md`、`visual-review.md`、`recipes/`；`scripts/visual_qa.py`、`scripts/visualization_style.py` |
| `paper-writer` | `paper-playbook.md`、`latex-format.md`、`abstract-writing.md`、`deai-writing.md`、`deai-writing-en.md`、`artifact-registry.md` |
| `independent-reviewer` | `review-playbook.md`、`checklist-opt.md`、`checklist-stats.md`、`abstract-writing.md`、`competition-conventions.md`、`optimization-conventions.md`、`data-conventions.md`、`chart-library.md`、`game-theory-conventions.md` |
| `pipeline-protocol` | 无 references；正文已自包含（覆盖契约、工具、门、拓扑） |

### 旧角色全文

`legacy-solver-opt.md`、`legacy-solver-stats.md`、`legacy-paper-writer.md`、`legacy-independent-reviewer.md` 从 `.trae/agents/` 归档到 `system/archive/legacy/`，**不进入运行期 skill**。

## 为什么这样做

- 运行期只读 `references/`，不再跳 `.trae` 大文件；上下文更可控。
- 规范/检查单/方法卡是“知识”，复制进 references；角色流程是“行为”，在 `SKILL.md` 里保持短小。
- 旧全文不删，归档在 `system/archive/legacy/`，需要追溯时看；不在 skill 里留 `.trae` 指针。
- 代码检查器（`check_solution_json.py` 等）仍走 `.trae/code_templates/`，因为 `checks.json` 和 Kernel 都按该路径调用；Phase 3 再迁 `tools/`。这是**工具路径**，不是 prompt 知识依赖。

## 验证

- `.dsh/skills/` 下 `grep '\.trae/(agents|papers|skills)'` → **0 命中**。
- 7 个 `SKILL.md` 均 **≤4KB**（最大 `pipeline-protocol` 3761B）。
- references 文件数：solver-opt 16、solver-stats 18、method 3、figure 13、paper 6、reviewer 9。
- 技能 catalog 仍自动发现 7 个 skill；加载 `pipeline-protocol` 正常返回。

## 经验

1. **自包含 ≠ 把旧大文件塞进 skill**：先蒸馏 playbook，再把规范/卡片作为 references；旧全文归档。
2. **不要留 `.trae` 知识指针**：只要 `SKILL.md` 或 reference 还指向 `.trae`，运行期就仍有隐性依赖；用 grep 做验收。
3. **工具路径和知识路径分开**：检查器/模板是工具，可以暂时留在 `.trae/code_templates`；不要在 Phase 2C 强行搬，避免破坏 `checks.json`。
4. **references 用相对路径**：`references/...`、`scripts/...`，从 skill base dir 解析；不要写绝对路径。
5. **最小加载**：`SKILL.md` 只写“何时用/必做/禁做/交付/提交”，细节按需读 reference。
