#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pipeline_kernel.py — Phase 1 Kernel MVP 单元/集成测试

运行：
  .venv/Scripts/python.exe -m unittest tools/test_pipeline_kernel.py -v

覆盖：
  - 完整状态机（no-checks 测试模式）
  - gate 前置条件
  - G1 rollback → fresh_dossier → 计划门 → 回归 → T55 回 METHOD
  - G2 local return → resume → stale 排除 METHOD → T55 回 FIGURES
  - freshness solver/reviewer 模式
  - 回归失败阻塞
  - route 最早 stale 下游
  - 真实 INTAKE 机查（需要可生成 PDF 的 matplotlib；不可用则跳过）
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pipeline_kernel as k

REPO = Path(__file__).resolve().parent.parent
STATEMENT = (
    "# 合成测试题\n\n"
    "某工厂生产两种产品，产品 A 的单位利润为 80 元，产品 B 的单位利润为 120 元。"
    "每件 A 需要 2 小时加工和 1 单位原料，每件 B 需要 3 小时加工和 2 单位原料。"
    "可用加工时间为 120 小时，可用原料为 80 单位。A 的产量不超过 30，B 的产量不超过 20。"
    "要求建立线性规划模型，最大化总利润，给出最优产量、最优目标值和影子价格解释，"
    "并讨论 A 的单位利润在 60 到 100 之间变化时的策略转换临界点。"
    "最后讨论原料供应不确定时的蒙特卡洛稳健性验证。\n"
)


class KernelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kernel-test-"))
        (self.tmp / "赛题").mkdir(parents=True, exist_ok=True)
        (self.tmp / "赛题" / "题面.md").write_text(STATEMENT, encoding="utf-8")
        (self.tmp / "赛题" / "ingest_report.json").write_text(
            json.dumps({"source": "synthetic", "pages": 1, "error_count": 0}), encoding="utf-8"
        )
        self.fw = k.load_framework()
        self.ck = k.load_checks()
        k.start(self.tmp, "opt", "balanced", "cumcm", run_id="test", force=True)
        k.submit(self.tmp, "INTAKE", "lead", "lead", self.ck, self.fw, no_checks=True)
        k.gate(self.tmp, "G0", "approve", "test", self.ck, self.fw)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def state(self):
        return k.load_state(self.tmp)

    def to_method_gate(self):
        k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        k.submit(self.tmp, "METHOD", "method", "method", self.ck, self.fw, no_checks=True)
        self.assertEqual(self.state()["stage"], "METHOD_GATE")

    def to_model_review(self, with_figure=True):
        self.to_method_gate()
        k.gate(self.tmp, "G1", "proceed", "ok", self.ck, self.fw)
        if with_figure:
            figs = self.tmp / "result_bundle" / "figures"
            figs.mkdir(parents=True, exist_ok=True)
            (figs / "fig1.pdf").write_bytes(b"%PDF-1.4\n% synthetic\n")
        k.submit(self.tmp, "FIGURES", "figures", "figures", self.ck, self.fw, no_checks=True)
        self.assertEqual(self.state()["stage"], "MODEL_REVIEW")

    def write_review(self, high: bool, round_no: int = 1):
        report = {
            "round": round_no,
            "verdict": "REJECT" if high else "PASS",
            "high_severity_count": 1 if high else 0,
            "findings": ([{"severity": "high", "location": "paper.tex", "message": "synthetic"}] if high else []),
        }
        p = self.tmp / "decision_logs" / "review_report.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report), encoding="utf-8")

    def write_plan(self, pass_regression=True, include_f1=True):
        dossier = json.loads((self.tmp / "decision_logs" / "failure_dossier.json").read_text(encoding="utf-8"))
        plan = {
            "run_id": "test",
            "dossier_ids": [dossier["dossier_id"]],
            "approach": {"method": "revised LP", "algorithm": "LP", "model_structure": "revised",
                         "why_it_avoids_failure": "explicit validation"},
            "changes": ([{"failure_mode_id": "F1", "countermeasure": "revised formulation",
                          "verification": "sensitivity", "residual_risk": "low"}] if include_f1 else []),
            "unchanged_parts": [],
            "similarity_to_rejected": {"materially_same": False, "justification": "changed",
                                        "new_evidence": "new validation"},
            "regression_checks": ([{"failure_mode_id": "F1",
                                    "command": "python -c \"import sys; sys.exit(0)\"" if pass_regression else "python -c \"import sys; sys.exit(1)\"",
                                    "expected": "exit 0", "evidence": "synthetic"}] if include_f1 else []),
            "risks": [],
            "budget": {"wall_minutes": 60, "token_estimate": 1000},
        }
        (self.tmp / "decision_logs" / "rework_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def test_gate_precondition(self):
        # Fresh run without the INTAKE submit must refuse G0.
        other = Path(tempfile.mkdtemp(prefix="kernel-pre-"))
        try:
            k.start(other, "opt", "balanced", "cumcm", run_id="pre", force=True)
            with self.assertRaises(k.KernelError):
                k.gate(other, "G0", "approve", "no submit", self.ck, self.fw)
        finally:
            shutil.rmtree(other, ignore_errors=True)

    def test_full_state_machine(self):
        k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        k.submit(self.tmp, "METHOD", "method", "method", self.ck, self.fw, no_checks=True)
        k.gate(self.tmp, "G1", "proceed", "ok", self.ck, self.fw)
        k.submit(self.tmp, "FIGURES", "figures", "figures", self.ck, self.fw, no_checks=True)
        k.gate(self.tmp, "G2", "approve", "ok", self.ck, self.fw)
        k.submit(self.tmp, "WRITING", "writer", "writer", self.ck, self.fw, no_checks=True)
        k.gate(self.tmp, "G3", "approve", "ok", self.ck, self.fw)
        self.write_review(high=True)
        k.submit(self.tmp, "REVIEW", "reviewer", "reviewer", self.ck, self.fw, no_checks=True)
        self.assertEqual(self.state()["stage"], "FIX_R1")
        k.submit(self.tmp, "FIX_R1", "writer", "writer", self.ck, self.fw, no_checks=True)
        self.write_review(high=False)
        k.submit(self.tmp, "RE_REVIEW_R1", "reviewer", "reviewer", self.ck, self.fw, no_checks=True)
        self.assertEqual(self.state()["stage"], "COMPLIANCE")
        k.submit(self.tmp, "COMPLIANCE", "lead", "kernel", self.ck, self.fw, no_checks=True)
        k.gate(self.tmp, "G5", "deliver", "ok", self.ck, self.fw)
        self.assertEqual(self.state()["stage"], "DELIVERED")
        self.assertEqual(self.state()["status"], "DELIVERED")

    def test_g1_rollback_fresh_dossier_and_plan_gate(self):
        self.to_method_gate()
        k.gate(self.tmp, "G1", "rollback", "method mismatch", self.ck, self.fw, scope="root", root_cause="method_mismatch")
        st = self.state()
        self.assertEqual(st["stage"], "MODELING")
        self.assertEqual(st["rework"]["mode"], "fresh_dossier")
        self.assertEqual(st["rework"]["return_to"], "METHOD")
        self.assertTrue((self.tmp / "decision_logs" / "failure_dossier.json").exists())
        blocked = k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["phase"], "plan_gate")
        self.write_plan(pass_regression=True)
        result = k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        self.assertTrue(result["ok"])
        st = self.state()
        self.assertEqual(st["stage"], "METHOD")
        self.assertFalse(st["rework"]["active"])
        self.assertTrue((self.tmp / "decision_logs" / "regression_check_report.json").exists())

    def test_g1_rollback_local_resume(self):
        self.to_method_gate()
        k.gate(self.tmp, "G1", "rollback", "local scope expansion", self.ck, self.fw,
               scope="local", root_cause="model_structure")
        st = self.state()
        self.assertEqual(st["stage"], "MODELING")
        self.assertEqual(st["rework"]["mode"], "resume")
        self.assertEqual(st["rework"]["return_to"], "METHOD")
        self.assertNotIn("METHOD", st["stale_stages"])
        self.assertFalse((self.tmp / "decision_logs" / "failure_dossier.json").exists())
        result = k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        self.assertTrue(result["ok"])
        self.assertEqual(self.state()["stage"], "METHOD")
        self.assertFalse(self.state()["rework"]["active"])

    def test_g1_local_brief_carries_tickets(self):
        self.to_method_gate()
        critique = self.tmp / "decision_logs" / "method_critique.json"
        critique.write_text(
            json.dumps({"tickets": [{"level": "更紧", "alternative": "fix critical points", "action": "optional"}]}),
            encoding="utf-8",
        )
        k.gate(self.tmp, "G1", "rollback", "local ticket", self.ck, self.fw, scope="local")
        brief = json.loads((self.tmp / "decision_logs" / "rework_brief.json").read_text(encoding="utf-8"))
        self.assertEqual(len(brief["tickets"]), 1)
        self.assertIn("fix critical points", brief["change"])
        self.assertIn("decision_logs/method_critique.json", brief["must_read"])

    def test_local_resume_excludes_method(self):
        self.to_model_review(with_figure=True)
        k.gate(self.tmp, "G2", "return_modeling", "one numeric bug", self.ck, self.fw, scope="local")
        st = self.state()
        self.assertEqual(st["stage"], "MODELING")
        self.assertEqual(st["rework"]["mode"], "resume")
        self.assertEqual(st["rework"]["return_to"], "FIGURES")
        self.assertNotIn("METHOD", st["stale_stages"])
        self.assertIn("FIGURES", st["stale_stages"])
        result = k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        self.assertTrue(result["ok"])
        self.assertEqual(self.state()["stage"], "FIGURES")

    def test_freshness_modes(self):
        r1 = k.freshness(self.tmp, "solver", "local_fix", "local", affected=1, child_id="s1")
        self.assertEqual(r1["decision"]["mode"], "resume")
        r2 = k.freshness(self.tmp, "solver", "method_blocked", "root", affected=2)
        self.assertEqual(r2["decision"]["mode"], "fresh_dossier")
        r3 = k.freshness(self.tmp, "reviewer", "local_fix", "local", round_no=1)
        self.assertEqual(r3["decision"]["mode"], "resume")
        r4 = k.freshness(self.tmp, "reviewer", "high_failure", "root", round_no=2)
        self.assertEqual(r4["decision"]["mode"], "fresh")
        st = self.state()
        self.assertGreaterEqual(len(st["freshness_decisions"]), 4)
        self.assertEqual(st["subagent_ids"]["solver"], "s1")

    def test_regression_failure_blocks(self):
        self.to_method_gate()
        k.gate(self.tmp, "G1", "rollback", "root cause", self.ck, self.fw, scope="root")
        self.write_plan(pass_regression=False)
        result = k.submit(self.tmp, "MODELING", "solver", "solver", self.ck, self.fw, no_checks=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["phase"], "regression")
        self.assertEqual(self.state()["stage"], "MODELING")

    def test_route_earliest_stale(self):
        st = self.state()
        st["stale_stages"] = ["WRITING", "REVIEW", "FIGURES"]
        k.save_state(self.tmp, st)
        result = k.route(self.tmp)
        self.assertEqual(result["return_to"], "FIGURES")

    @unittest.skipUnless(os.environ.get("RUN_KERNEL_INTEGRATION") == "1", "set RUN_KERNEL_INTEGRATION=1 for real checks")
    def test_real_intake_checks(self):
        # Requires matplotlib to make a tiny PDF and the repo's Python env.
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        pdf_path = self.tmp / "赛题" / "题目.pdf"
        fig = plt.figure(figsize=(8.27, 11.69))
        lines = [
            "Synthetic problem for kernel integration test.",
            "A factory produces two products, A and B.",
            "Product A gives profit 80 and uses 2 hours and 1 unit of material.",
            "Product B gives profit 120 and uses 3 hours and 2 units of material.",
            "Available: 120 hours and 80 units.",
            "A <= 30 and B <= 20.",
            "Maximize total profit and find the optimal solution.",
            "Give shadow prices for hours and material.",
            "Discuss the critical point when A profit varies from 60 to 100.",
            "Discuss Monte Carlo robustness under material uncertainty.",
            "This is a synthetic problem for kernel testing only.",
        ]
        fig.text(0.08, 0.94, "Synthetic Problem Statement", fontsize=14)
        for index, line in enumerate(lines):
            fig.text(0.08, 0.88 - index * 0.045, line, fontsize=9)
        with PdfPages(pdf_path) as pdf:
            pdf.savefig(fig)
        plt.close(fig)
        # Reset state with force while keeping the synthetic statement/PDF.
        k.start(self.tmp, "opt", "balanced", "cumcm", run_id="test", force=True)
        result = k.submit(self.tmp, "INTAKE", "lead", "lead", self.ck, self.fw, no_checks=False)
        self.assertTrue(result["ok"], msg=json.dumps(result, ensure_ascii=False)[:4000])
        self.assertEqual(self.state()["last_check_summary"]["stage"], "INTAKE")


    def test_normalize_report_explicit_counts_not_double_counted(self):
        report = self.tmp / "manifest_check_report.json"
        report.write_text(
            json.dumps(
                {
                    "error_count": 0,
                    "warn_count": 1,
                    "errors": [],
                    "warns": [{"item": "题面附件转写", "msg": "条件产物缺失"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        check = {"id": "intake_manifest", "stage": "INTAKE", "blocking": "ERROR",
                 "reports": ["manifest_check_report.json"]}
        result = k.normalize_report(check, self.tmp, 0, "", "", 0)
        self.assertEqual(result["warn_count"], 1)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["status"], "warn")


if __name__ == "__main__":
    unittest.main(verbosity=2)
