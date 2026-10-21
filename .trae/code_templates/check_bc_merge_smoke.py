#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BC 并轨 T11 冒烟。临时目录用完即删。"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).resolve().parent
AGENTS = ROOT / ".trae" / "agents"
PAPERS = ROOT / ".trae" / "papers"


def run(script, args):
    return subprocess.run(
        [sys.executable, str(TEMPLATES / script), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def fail(msg):
    print("FAIL", msg)
    sys.exit(1)


def main():
    opt_agent = (AGENTS / "modeling-solver-opt.md").read_text(encoding="utf-8")
    stats_agent = (AGENTS / "modeling-solver-stats.md").read_text(encoding="utf-8")
    if "数据方法卡片" in opt_agent:
        fail("opt 提示词含数据方法卡片目录")
    for banned in ("MIPGap", "active_constraints", "Tornado"):
        if banned in stats_agent:
            fail(f"stats 提示词含 {banned}")
    if "figures/" in opt_agent and "不得出图" not in opt_agent:
        fail("opt 未禁止出图")
    if "不得出图" not in stats_agent:
        fail("stats 未禁止出图")

    orch = (ROOT / ".trae" / "rules" / "orchestrator.md").read_text(encoding="utf-8")
    if "不喂另一轨的 gate" not in orch or "gate_stats.md" not in orch:
        fail("编排器未按轨喂闸门")
    agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if "返工仍调用本轨" not in agents_md and "返工仍调这一个名字" not in orch:
        fail("返工未钉在本轨建模岗")
    if "modeling-solver-stats" not in agents_md:
        fail("AGENTS 未登记 stats 建模岗")

    opt_sol = {
        "问题一": {
            "objective_value": 10,
            "decision_variables": {"x": [1]},
            "solver": "HiGHS",
            "optimality": {"mip_gap": 0.0, "status": "optimal"},
            "active_constraints": [{"name": "cap", "status": "active", "slack": 0.0}],
            "sensitivity": {"parameters": ["demand ±20%"]},
            "critical_points": [{"value": 5, "source": "scan"}],
            "monte_carlo": {
                "n_sim": 1000,
                "convergence": "converged (std/mean=2% < 5% threshold)",
                "std_mean_ratio": 0.02,
                "deviation": 0.01,
            },
        }
    }
    opt_fp = {
        "problem_type": "LP",
        "variable_type": "continuous",
        "variable_count_estimate": "small<10",
        "objective_type": "linear",
        "constraint_type": "linear_only",
        "constraint_count_estimate": "small<20",
        "time_dependence": "static",
        "uncertainty": "none",
        "data_role": "given",
        "theoretical_challenge": "none_obvious",
        "confidence": "high",
        "data_quality": {"shape": "1x1", "missing": "0", "outlier": "0", "distribution": "n/a"},
        "overlays": [],
        "linearized": "false",
    }
    stats_sol = {
        "问题一": {
            "task_type": "regression",
            "objective_or_goal": "拟合",
            "metrics": {"RMSE": {"value": 1.2, "split": "test"}},
            "model": {"name": "ols", "selection": "ridge vs baseline mean"},
            "validation": {"method": "kfold_cv", "scores": {"RMSE": 1.2}, "overfitting_check": "train 0.2 test 0.3"},
            "preprocessing": {
                "missing": "none",
                "outliers": "none",
                "encoding": "none",
                "scaling": "standard",
                "train_test_isolation": "scaler fit on training fold only, never on the full sample",
            },
            "data_lineage": "annex",
            "sensitivity": {"parameters": ["feature ±20%"]},
            "monte_carlo": None,
        }
    }
    stats_fp = {
        "problem_type": "Regression",
        "task_types": ["Regression"],
        "data_structure": "cross_section",
        "sample_scale": "small<100",
        "dimension": "low(p<<n)",
        "data_role": "附件给定",
        "downstream_optimization": "no",
        "experimental_design": "no",
        "confidence": "high",
        "data_quality": "10 行，无缺失",
    }

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "result_bundle").mkdir()
        (root / "project").mkdir()
        (root / "project" / "solve.py").write_text("print(1)\n", encoding="utf-8")
        (root / "pipeline_state.json").write_text(
            json.dumps({"problem_track": "opt"}), encoding="utf-8")
        (root / "result_bundle" / "solution.json").write_text(
            json.dumps(opt_sol), encoding="utf-8")
        (root / "result_bundle" / "feature_fingerprint.json").write_text(
            json.dumps(opt_fp), encoding="utf-8")
        r = run("check_solution_json.py", [root / "result_bundle" / "solution.json", "--selfcheck"])
        if r.returncode != 0:
            fail("opt 机查\n" + r.stdout)
        r = run("check_modeling_artifacts.py", [root, "--scope", "modeling"])
        if r.returncode != 0:
            fail("opt 指纹/过早出图\n" + r.stdout)
        r = run("check_solution_json_stats.py", [root / "result_bundle" / "solution.json", "--selfcheck"])
        if r.returncode == 0:
            fail("opt 样例不该通过 stats 机查")

        (root / "pipeline_state.json").write_text(
            json.dumps({"problem_track": "stats"}), encoding="utf-8")
        (root / "result_bundle" / "solution.json").write_text(
            json.dumps(stats_sol), encoding="utf-8")
        (root / "result_bundle" / "feature_fingerprint.json").write_text(
            json.dumps(stats_fp), encoding="utf-8")
        r = run("check_solution_json_stats.py", [root / "result_bundle" / "solution.json", "--selfcheck"])
        if r.returncode != 0:
            fail("stats 机查\n" + r.stdout)
        r = run("check_leakage.py", [root / "project"])
        if r.returncode != 0:
            fail("leakage 应退出 0")
        r = run("check_modeling_artifacts.py", [root, "--scope", "modeling"])
        if r.returncode != 0:
            fail("stats 指纹\n" + r.stdout)
        r = run("check_solution_json.py", [root / "result_bundle" / "solution.json", "--selfcheck"])
        if r.returncode == 0:
            fail("stats 样例不该通过 opt 机查")

    r = subprocess.run(
        [sys.executable, str(TEMPLATES / "test_contract_checks.py"),
         "TestCheckAbstractGuard.test_shuwei_en_locate_abstract_cmd",
         "TestCheckLatexCompliance.test_shuwei_en_allows_toc_maketitle",
         "TestCheckLatexCompliance.test_shuwei_fixture_toc_errors_under_cumcm"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        fail("shuwei 回归\n" + r.stdout + r.stderr)
    print("PASS T11 冒烟")


if __name__ == "__main__":
    main()
