#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_contract_checks.py — 四个契约机查脚本的单元测试（D19）

覆盖脚本与关键判定路径：
  check_solution_json.py    契约字段缺失 / convergence 矛盾 / 报告规范路径与回退
  check_pipeline_manifest.py 必填缺失 / 契约外编号（1-4 合法、5+ 非法）/ 术语表双份 / --report
  check_latex_compliance.py  \\tableofcontents 违规 / 最小合规夹具 / 参考文献年份晚于赛题
  check_isolation.py        提取物散放 / 签名命中非授权产出 / 命中 calibration 缺隔离声明 / 无签名跳过

运行：python .trae/code_templates/test_contract_checks.py [-v]
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent


def run_script(script, args):
    """以子进程运行机查脚本，返回 CompletedProcess（utf-8 捕获）。"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, str(TEMPLATES / script), *[str(a) for a in args]],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


# ---------- 夹具 ----------

VALID_SOLUTION = {
    "问题一": {
        "objective_value": 123.45,
        "decision_variables": {"x": [1, 2, 3]},
        "solver": "HiGHS",
        "optimality": {"mip_gap": 0.0},
        "active_constraints": [{"name": "cap", "status": "active", "slack": 0.0}],
        "sensitivity": {"param": "p", "range": [0.9, 1.1], "data": [1.0, 2.0]},
        "critical_points": [{"value": 5, "source": "solution.json"}],
        "monte_carlo": {"runs": 1000,
                        "convergence": "converged (std/mean=2% < 5% threshold)",
                        "std_mean_ratio": 0.02, "deviation": 0.01},
    }
}

_ABSTRACT = "。".join(
    f"针对第{i}个子问题建立相应优化模型并编程求解，结果表明该情形下目标值稳定，参数扰动后结论保持一致"
    for i in range(1, 11)) + "。"  # 约 450 字，落在 400-800 区间

_FIGURES = "\n".join(
    "\\begin{figure}[htbp]\n\\centering\n"
    f"\\includegraphics[width=0.8\\textwidth]{{fig{i}.pdf}}\n"
    f"\\caption{{第{i}种情形下的结果对比}}\n\\label{{fig:{i}}}\n\\end{{figure}}"
    for i in range(1, 7))

_BIB = "\n".join(
    f"\\bibitem{{r{i}}} 作者{i}. 优化方法及其应用研究[J]. 某学报, 2015."
    for i in range(1, 11))

VALID_TEX = f"""\\documentclass{{ctexart}}
\\pagestyle{{plain}}
\\ctexset{{section={{name={{,、}}}}}}
\\usepackage{{graphicx}}
\\usepackage{{listings}}
\\begin{{document}}
\\begin{{center}}{{\\zihao{{3}}\\heiti 基于优化模型的调度问题研究}}\\end{{center}}
\\section*{{摘要}}
{_ABSTRACT}

关键词：混合整数规划；灵敏度分析；蒙特卡洛仿真；启发式算法
\\section{{问题重述}}
本文研究某调度优化问题，将其提炼为三个明确的数学任务。
\\section{{问题分析}}
各子问题的核心难点在于约束耦合与规模增长，拟采用精确求解与启发式相结合的路线。
\\section{{模型假设}}
假设需求在规划期内保持平稳；假设各环节容量已知且固定。
\\section{{符号说明}}
$x_i$ 表示第 $i$ 个节点的分配量，单位为件。
\\section{{模型的建立与求解}}
目标函数取总成本最小，约束包含容量限制与需求覆盖，求解采用分支定界。
结果如图 \\ref{{fig:1}}、图 \\ref{{fig:2}}、图 \\ref{{fig:3}}、图 \\ref{{fig:4}}、图 \\ref{{fig:5}}、图 \\ref{{fig:6}} 所示。
{_FIGURES}
\\section{{灵敏度与误差分析}}
对核心参数施加扰动并绘制龙卷风图，模型输出对关键参数的敏感度有限。
\\section{{模型评价与推广}}
模型结构清晰，可推广至同类资源配置场景；局限在于对静态需求假设的依赖。
\\begin{{thebibliography}}{{99}}
{_BIB}
\\end{{thebibliography}}
\\appendix
\\section{{附录}}
\\lstinputlisting{{main_code.py}}
\\end{{document}}
"""


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, (dict, list)):
            p.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            p.write_text(content, encoding="utf-8")
        return p


# ---------- check_solution_json.py ----------

class TestCheckSolutionJson(Base):
    SCRIPT = "check_solution_json.py"

    def test_valid_report_at_project_root(self):
        sol = self.write("result_bundle/solution.json", VALID_SOLUTION)
        r = run_script(self.SCRIPT, [sol])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / "contract_check_report.json").is_file(),
                        "报告应落盘项目根（result_bundle 上两级）")

    def test_missing_required_fields_error(self):
        bad = {"问题一": {k: v for k, v in VALID_SOLUTION["问题一"].items()
                        if k not in ("sensitivity", "critical_points",
                                     "active_constraints", "monte_carlo")}}
        sol = self.write("result_bundle/solution.json", bad)
        r = run_script(self.SCRIPT, [sol])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("缺必填字段", r.stdout)

    def test_convergence_contradiction_error(self):
        import copy
        bad = copy.deepcopy(VALID_SOLUTION)
        bad["问题一"]["monte_carlo"]["convergence"] = "converged (std/mean=20% < 5% threshold)"
        bad["问题一"]["monte_carlo"]["std_mean_ratio"] = 0.20
        sol = self.write("result_bundle/solution.json", bad)
        r = run_script(self.SCRIPT, [sol])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("矛盾", r.stdout)

    def test_report_fallback_same_dir(self):
        """solution.json 不在 result_bundle/ 下 → 报告回退同目录并 WARN 提示。"""
        sol = self.write("solution.json", VALID_SOLUTION)
        r = run_script(self.SCRIPT, [sol])
        self.assertIn("回退落盘同目录", r.stdout)
        self.assertTrue((self.root / "contract_check_report.json").is_file())


# ---------- check_pipeline_manifest.py ----------

class TestCheckPipelineManifest(Base):
    SCRIPT = "check_pipeline_manifest.py"
    INTAKE_TEXT = "赛题转写占位。" * 40  # 非空白 >200 字

    def write_intake(self):
        self.write("赛题/题面.md", self.INTAKE_TEXT)
        self.write("赛题/ingest_report.json", {"error_count": 0, "chars": 280})

    def run_manifest(self, stage="modeling", report=False):
        args = ["--project-root", self.root, "--stage", stage]
        if report:
            args.append("--report")
        return run_script(self.SCRIPT, args)

    def test_empty_project_errors(self):
        r = self.run_manifest()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertGreater(json.loads(r.stdout)["error_count"], 0)

    def test_forbidden_handoff_5(self):
        self.write("handoff_notes_5.md", "x")
        r = self.run_manifest()
        self.assertIn("契约外 handoff_notes 编号", r.stdout)

    def test_handoff_3_4_allowed(self):
        """编号 3/4 已注册（D1+D8 修复），不得判为契约外编号。"""
        self.write("handoff_notes_3.md", "x")
        self.write("handoff_notes_4.md", "x")
        r = self.run_manifest()
        self.assertNotIn("契约外 handoff_notes 编号", r.stdout)

    def test_glossary_duplication(self):
        self.write("术语表.json", {})
        self.write("result_bundle/术语表.json", {})
        r = self.run_manifest()
        self.assertIn("双份并存", r.stdout)

    def test_report_written(self):
        r = self.run_manifest(report=True)
        rep = self.root / "manifest_check_report.json"
        self.assertTrue(rep.is_file())
        self.assertEqual(json.loads(rep.read_text(encoding="utf-8"))["stage"], "modeling")

    def test_modeling_stage_full_pass(self):
        """全齐夹具：modeling 阶段必填产物齐备（不含出图）→ exit 0 放行。"""
        self.write_intake()
        for rel in ("result_bundle/solution.json", "result_bundle/modeling_plan.json",
                    "result_bundle/feature_fingerprint.json", "result_bundle/术语表.json"):
            self.write(rel, {})
        self.write("handoff_notes_1.md", "x")
        for name in ("s1_reflection", "guided_questions_trace", "s2_reflection",
                     "s3_reflection"):
            self.write(f"decision_logs/{name}.md", "x")
        # 卡片匹配日志须逐卡点名（新格式矩阵行），否则触发全覆盖 ERROR
        card_rows = "\n".join(f"| {i:02d} | 排除 | 特征指纹不符 |" for i in range(1, 13))
        self.write("decision_logs/method_card_matching.md", f"## 匹配矩阵\n{card_rows}\n")
        self.write("contract_check_report.json", {})
        self.write("modeling_artifacts_report.json", {})
        self.write("code_hygiene_report.json", {})
        self.write("workspace_hygiene_report.json", {})
        self.write("pipeline_state.json", {})
        r = self.run_manifest(report=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_modeling_stage_does_not_require_figures(self):
        """出图已拆到 figures 阶段：modeling 门缺 figures 不得拦。"""
        self.write_intake()
        for rel in ("result_bundle/solution.json", "result_bundle/modeling_plan.json",
                    "result_bundle/feature_fingerprint.json", "result_bundle/术语表.json"):
            self.write(rel, {})
        self.write("handoff_notes_1.md", "x")
        for name in ("s1_reflection", "guided_questions_trace", "s2_reflection",
                     "s3_reflection"):
            self.write(f"decision_logs/{name}.md", "x")
        card_rows = "\n".join(f"| {i:02d} | 排除 | 特征指纹不符 |" for i in range(1, 13))
        self.write("decision_logs/method_card_matching.md", f"## 匹配矩阵\n{card_rows}\n")
        self.write("contract_check_report.json", {})
        self.write("modeling_artifacts_report.json", {})
        self.write("code_hygiene_report.json", {})
        self.write("workspace_hygiene_report.json", {})
        self.write("pipeline_state.json", {})
        r = self.run_manifest()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("figures 目录", r.stdout)

    def test_intake_stage_requires_statement(self):
        r = self.run_manifest(stage="intake")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("题面.md", r.stdout)

    def test_intake_stage_too_short_errors(self):
        self.write("赛题/题面.md", "太短")
        self.write("赛题/ingest_report.json", {"error_count": 0})
        r = self.run_manifest(stage="intake")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("题面转写过短", r.stdout)

    def test_intake_stage_full_pass(self):
        self.write_intake()
        r = self.run_manifest(stage="intake", report=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads((self.root / "manifest_check_report.json").read_text(encoding="utf-8"))["stage"], "intake")

    def test_figures_stage_requires_six_pdfs_and_清单(self):
        """figures 阶段：缺 ≥6 PDF 或图表清单 → ERROR。"""
        r = self.run_manifest(stage="figures")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("figures 目录", r.stdout)

    def test_method_card_missing_card_error(self):
        """卡片匹配日志漏掉某张卡片（早停/跳卡）→ ERROR 拦截。"""
        self.write("decision_logs/method_card_matching.md",
                   "## 匹配矩阵\n| 01 | 命中 | 线性目标 |\n| 02 | 排除 | 无离散变量 |\n")
        r = self.run_manifest()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("卡片编号未逐一点名", r.stdout)

    def test_method_card_legacy_format_pass(self):
        """旧格式'卡片 NN'表述向后兼容：12 张全点名 → 不触发全覆盖 ERROR。"""
        legacy = "\n".join(f"### 卡片 {i:02d}：不匹配\n理由：特征指纹不符\n" for i in range(1, 13))
        self.write("decision_logs/method_card_matching.md", legacy)
        r = self.run_manifest()
        self.assertNotIn("卡片编号未逐一点名", r.stdout)


# ---------- check_latex_compliance.py ----------

class TestCheckLatexCompliance(Base):
    SCRIPT = "check_latex_compliance.py"

    def setup_tex(self, text=VALID_TEX):
        tex = self.write("paper.tex", text)
        self.write("main_code.py", "print('ok')\n")
        return tex

    def test_minimal_compliant(self):
        tex = self.setup_tex()
        r = run_script(self.SCRIPT, [tex, self.root])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue((self.root / "latex_compliance_report.json").is_file())

    def test_tableofcontents_error(self):
        tex = self.setup_tex(VALID_TEX.replace(
            "\\begin{document}", "\\begin{document}\n\\tableofcontents"))
        r = run_script(self.SCRIPT, [tex, self.root])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("tableofcontents", r.stdout)

    def test_future_reference_year_error(self):
        """文献年份 2015 晚于 --contest-year=2010 → ERROR（时代错位）。"""
        tex = self.setup_tex()
        r = run_script(self.SCRIPT, [tex, self.root, "--contest-year=2010"])
        self.assertEqual(r.returncode, 1, r.stdout)
        rep = json.loads((self.root / "latex_compliance_report.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(rep["summary"]["ERROR"], 1)


# ---------- check_tex_numbers.py ----------

class TestCheckTexNumbers(Base):
    SCRIPT = "check_tex_numbers.py"

    def setup_pair(self, tex_body):
        tex = self.write("paper.tex", tex_body)
        sol = self.write("result_bundle/solution.json", VALID_SOLUTION)
        return tex, sol

    def test_all_matched(self):
        """正文数值均命中 solution.json（容差内四舍五入视为命中）→ WARN 0。"""
        tex, sol = self.setup_pair("结果目标值为 123.45，蒙特卡洛仿真 1000 次，扰动后 1.10 倍。")
        r = run_script(self.SCRIPT, [tex, sol])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("WARN", r.stdout)

    def test_unmatched_warn_not_block(self):
        """正文含 solution.json 没有的高精度数值 → WARN 但 exit 0（不阻塞）。"""
        tex, sol = self.setup_pair("某处数值 987.65 与结果无关。")
        r = run_script(self.SCRIPT, [tex, sol])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WARN", r.stdout)

    def test_year_excluded(self):
        """年份（19xx/20xx）不参与比对。"""
        tex, sol = self.setup_pair("本文基于 2023 年公开数据展开分析。")
        r = run_script(self.SCRIPT, [tex, sol])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("WARN", r.stdout)

    def test_report_written(self):
        tex, sol = self.setup_pair("结果 123.45。")
        r = run_script(self.SCRIPT, [tex, sol, "--report"])
        self.assertEqual(r.returncode, 0, r.stdout)
        rep = self.root / "tex_number_check_report.json"
        self.assertTrue(rep.is_file())
        self.assertIn("warn_count", json.loads(rep.read_text(encoding="utf-8")))


# ---------- check_isolation.py ----------

class TestCheckIsolation(Base):
    SCRIPT = "check_isolation.py"
    SIG = "专有特征串ABC12345"

    def run_iso(self, *sigs, report=True):
        args = ["--project-root", self.root]
        for s in sigs:
            args += ["--signature", s]
        if report:
            args.append("--report")
        return run_script(self.SCRIPT, args)

    def test_scattered_extract_error(self):
        self.write("ref_notes.txt", "提取物")
        r = self.run_iso()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("散放", r.stdout)

    def test_quarantine_dir_exempt(self):
        """_quarantine/ 内的提取物属规范存放，不报散放。"""
        self.write("decision_logs/_quarantine/ref_notes.txt", "提取物")
        r = self.run_iso()
        self.assertNotIn("散放", r.stdout)

    def test_signature_leak_unauthorized(self):
        self.write("paper.tex", f"正文引用 {self.SIG} 的内容")
        r = self.run_iso(self.SIG)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("非授权产出含参照论文特征串", r.stdout)

    def test_signature_in_calibration_warn(self):
        self.write("calibration_report.md", f"对标 {self.SIG} 的分析")
        r = self.run_iso(self.SIG)
        self.assertEqual(r.returncode, 0, r.stdout)
        rep = json.loads((self.root / "isolation_check_report.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(rep["warn_count"], 1)

    def test_no_signature_skips_content(self):
        """无 --signature：只查散放、不查内容泄漏。"""
        self.write("paper.tex", f"正文引用 {self.SIG} 的内容")
        r = self.run_iso()
        self.assertEqual(r.returncode, 0, r.stdout)


# ---------- convert_problem.py ----------

class TestConvertProblem(Base):
    SCRIPT = "convert_problem.py"

    def test_missing_pdf_fails(self):
        r = run_script(self.SCRIPT, ["--project-root", self.root])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue((self.root / "赛题" / "ingest_report.json").is_file())

    def test_pdf_and_docx_to_markdown(self):
        import fitz
        from docx import Document

        pdf = self.root / "B题.pdf"
        doc = fitz.open()
        page = doc.new_page()
        line = "Problem 1: determine the shortest path and coverage range for the robot."
        for i in range(12):
            page.insert_text((72, 72 + i * 18), line)
        doc.save(str(pdf))
        doc.close()

        att_dir = self.root / "附件"
        att_dir.mkdir()
        d = Document()
        d.add_paragraph("协议字段说明与计时规则。" * 6)
        table = d.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "动作"
        table.cell(0, 1).text = "指令"
        table.cell(1, 0).text = "前进"
        table.cell(1, 1).text = "forward"
        d.save(str(att_dir / "附件1.docx"))

        r = run_script(self.SCRIPT, ["--project-root", self.root])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        md = (self.root / "赛题" / "题面.md").read_text(encoding="utf-8")
        self.assertIn("shortest path", md)
        self.assertIn("第 1 页", md)
        att = (self.root / "赛题" / "附件" / "附件1.md").read_text(encoding="utf-8")
        self.assertIn("协议字段说明", att)
        self.assertIn("forward", att)
        rep = json.loads((self.root / "赛题" / "ingest_report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["error_count"], 0)
        self.assertGreaterEqual(rep["chars"], 200)


# ---------- check_modeling_artifacts.py ----------

class TestCheckModelingArtifacts(Base):
    SCRIPT = "check_modeling_artifacts.py"

    def test_p11n_leaked_figure_errors(self):
        fig = self.root / "project" / "figures"
        fig.mkdir(parents=True)
        (fig / "fig_q1.png").write_bytes(b"\x89PNG\r\n")
        r = run_script(self.SCRIPT, [self.root, "--scope", "modeling"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("P11-N", r.stdout)
        self.assertIn("生成图", r.stdout)

    def test_p11n_pass_without_figures_dir(self):
        r = run_script(self.SCRIPT, [self.root, "--scope", "modeling"])
        self.assertIn("无生成图泄漏", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
